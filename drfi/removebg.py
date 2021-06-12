import os
import numpy as np
import cv2 as cv
from PIL import Image
import logging
from thumbor.filters import BaseFilter, filter_method

from .test import main

ROOT_FOLDER = os.getcwd()
SIMI_MODEL_PATH = os.path.join(ROOT_FOLDER, "data/model/rf_same_region.pkl")
SAL_MODEL_PATH = os.path.join(ROOT_FOLDER, "data/model/rf_salience.pkl")
FUSION_MODEL_PATH = os.path.join(ROOT_FOLDER, "data/model/mlp.pkl")


def get_bounding_box(mask):
    white_indices = np.where(mask == [255])
    white_coordinates = tuple(zip(white_indices[1], white_indices[0]))
    x, y, w, h = cv.boundingRect(np.array(white_coordinates))
    box = (x, y, x + w, y + h)
    return box


def grabcut(image, box, mask):
    mask = np.array(mask)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    mask[mask == 0] = cv.GC_BGD
    mask[mask == 255] = cv.GC_FGD
    print("get here")
    mask, bgdModel, fgdModel = cv.grabCut(
        image, mask, box, bgdModel, fgdModel, 10, cv.GC_INIT_WITH_MASK
    )
    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")
    image = image * mask2[:, :, np.newaxis]
    return image


class Filter(BaseFilter):
    @filter_method(BaseFilter.PositiveNumber)
    async def removebg(self, threshold):
        logging.info("threshold {}".format(threshold))
        image = self.engine.image
        image = image.convert("RGB")
        image = np.array(image)
        image = image[:, :, ::-1].copy()
        logging.info("width height {} {}".format(image.shape[0], image.shape[1]))
        mask, result_img = main(
            image, "mlp", SIMI_MODEL_PATH, SAL_MODEL_PATH, FUSION_MODEL_PATH, threshold
        )
        # result_img = cv.cvtColor(result_img, cv.COLOR_BGRA2RGBA)
        box = get_bounding_box(mask[:, :, 0])
        (x1, y1, x2, y2) = box
        result_img = grabcut(image[:, :, ::-1], box, mask[:, :, 0])
        result_img = cv.rectangle(result_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        img_pil = Image.fromarray(result_img)
        self.engine.image = img_pil
