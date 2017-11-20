import argparse
import os
import re
import cv2
import keras.backend as K
import numpy as np
import tensorflow as tf

from models.YOLOv2 import YOLOv2
from models.FeatureExtractor import FeatureExtractor

from utils.draw_boxes import DrawingBox
from utils.preprocess_img import preprocess_img
from utils.visualize import draw_bboxes

from cfg import ANCHORS, IMG_INPUT_SIZE, FEATURE_EXTRACTOR, N_CLASSES, CATEGORIES


parser = argparse.ArgumentParser("Over-fit model to validate loss function")

parser.add_argument('-p', '--path',
                    help="Path to image file", type=str, default=None)

parser.add_argument('-w', '--weights',
                    help="Path to pre-trained weight files", type=str, default=None)

parser.add_argument('-o', '--output-path',
                    help="Save image to output directory", type=str, default=None)

parser.add_argument('-i', '--iou',
                    help="IoU value for Non-max suppression", type=float, default=0.5)

parser.add_argument('-t', '--threshold',
                    help="Threshold value to display box", type=float, default=0.6)


def _main_():
    # ###############
    # Parse Config  #
    # ###############
    args = parser.parse_args()
    IMG_PATH  = args.path
    WEIGHTS   = args.weights
    OUTPUT    = args.output_path
    IOU       = args.iou
    THRESHOLD = args.threshold

    # Config Anchors
    anchors = []
    with open(ANCHORS, 'r') as f:
      data = f.read().splitlines()
      for line in data:
        numbers = re.findall('\d+.\d+', line)
        anchors.append((float(numbers[0]), float(numbers[1])))

    if not os.path.isfile(IMG_PATH):
        print("Image path is invalid.")
        exit()
    if not os.path.isfile(WEIGHTS):
        print("Weight file is invalid")
        exit()

    # Load class names
    with open(CATEGORIES, mode='r') as txt_file:
        class_names = [c.strip() for c in txt_file.readlines()]

    with tf.Session() as sess:

        # #################
        # Construct Graph #
        # #################
        darknet = FeatureExtractor(is_training=False, img_size=None, model=FEATURE_EXTRACTOR)
        yolo = YOLOv2(num_classes      = N_CLASSES,
                      anchors          = np.array(anchors),
                      is_training      = False,
                      feature_extractor=darknet,
                      detector         = FEATURE_EXTRACTOR)

        yolov2 = yolo.model
        yolov2.load_weights(WEIGHTS)

        img_shape = K.placeholder(shape=(2,))

        boxes, classes, scores = yolo.post_process(img_shape=img_shape,
                                                   n_classes      = N_CLASSES,
                                                   iou_threshold  = IOU,
                                                   score_threshold= THRESHOLD)

        # #####################
        # Process Image Input #
        # #####################
        orig_img = cv2.cvtColor(cv2.imread(IMG_PATH), cv2.COLOR_BGR2RGB)
        height, width, _ = orig_img.shape
        img = preprocess_img(cv2.resize(orig_img, (IMG_INPUT_SIZE, IMG_INPUT_SIZE)))
        img = np.expand_dims(img, 0)

        # #################
        # Make Prediction #
        # #################
        pred_bboxes, pred_classes, pred_scores = sess.run([boxes, classes, scores],
                                                          feed_dict={
                                                              yolov2.input: img,
                                                              img_shape: [height, width],
                                                              K.learning_phase(): 0
                                                          })
        # #################
        # Display Result  #
        # #################
        bboxes = []
        for box, cls, score in zip(pred_bboxes, pred_classes, pred_scores):
            y1, x1, y2, x2 = box
            bboxes.append(DrawingBox(x1, y1, x2, y2, class_names[cls], score))
            print("Found {} with {:2.1f}% on image {}".format(class_names[cls], score*100, IMG_PATH.split('/')[-1]))

        # Save image to evaluation dir
        if OUTPUT is not None:
            result = draw_bboxes(orig_img, bboxes)
            result.save(os.path.join(OUTPUT, IMG_PATH.split('/')[-1]))


if __name__ == "__main__":
    _main_()
    print("Done!")
