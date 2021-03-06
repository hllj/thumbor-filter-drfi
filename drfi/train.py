import cv2
import numpy as np

import os
import argparse

from model import RandomForest, MLP, XGB
from feature_process import Features
from region_detect import Super_Region, Region2Csv

# TRAIN_IMGS = 5000
C_LIST = [20, 80, 350, 900]
ROOT_FOLDER = os.getcwd()


class Img_Data:
    def __init__(self, img_path):
        self.img_path = img_path
        self.rlist, self.rmat = Super_Region.get_region(img_path, 100.0)
        features = Features(img_path, self.rlist, self.rmat)
        self.comb_features = features.comb_features
        self.rlists = [self.rlist]
        self.rmats = [self.rmat]
        self.feature93s = [features.features93]

    def get_multi_segs(self, rf):
        num_reg = len(self.rlist)
        similarity = np.ones([num_reg, num_reg])
        for i in range(num_reg):
            ids = self.comb_features[i]["j_ids"]
            X = self.comb_features[i]["features"]
            similarity[i, ids] = rf.predict(X)[:, 0]
        for c in C_LIST:
            rlist, rmat = Super_Region.combine_region(
                similarity, c, self.rlist, self.rmat
            )
            if len(rlist) == 1:
                continue
            self.rlists.append(rlist)
            self.rmats.append(rmat)
            features = Features(self.img_path, rlist, rmat, need_comb_features=False)
            self.feature93s.append(features.features93)


def get_fusion_model(fm):
    model = None
    if fm == "mlp":
        model = MLP()
    elif fm == "xgb":
        model = XGB()
    return model


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-ts", "--trainsize", required=True, help="Size of images for train model"
    )
    ap.add_argument(
        "-fm",
        "--fusionmodel",
        nargs="?",
        help="select model for fusion stage",
        const="mlp",
    )
    ap.add_argument(
        "-mpsr",
        "--modelpathsameregion",
        required=True,
        help="path to model predicting same region directory",
    )
    ap.add_argument(
        "-mps",
        "--modelpathsalience",
        required=True,
        help="path to model predict salience directory",
    )
    ap.add_argument(
        "-mpf",
        "--modelpathfusion",
        required=True,
        help="path to model fusion directory",
    )
    args = vars(ap.parse_args())

    TRAIN_IMGS = args["trainsize"]
    fm = args["fusionmodel"]
    model_path_same_region = args["modelpathsameregion"]
    model_path_salience = args["modelpathsalience"]
    model_path_fusion = args["modelpathfusion"]

    its = [i for i in range(0, TRAIN_IMGS) if i % 5 != 0]
    csv_paths = ["data/csv/train/{}.csv".format(i) for i in its]
    seg_csv_paths = ["data/csv/train/seg{}.csv".format(i) for i in its]
    w_csv_paths = ["data/csv/train/w{}.csv".format(i) for i in its]
    img_paths = ["data/MSRA-B/{}.jpg".format(i) for i in its]
    seg_paths = ["data/MSRA-B/{}.png".format(i) for i in its]
    img_datas = []
    for i in range(len(its)):
        print("finished simi {}".format(i))
        im_data = Img_Data(img_paths[i])
        Region2Csv.generate_similar_csv(
            im_data.rlist, im_data.comb_features, seg_paths[i], csv_paths[i]
        )
        img_datas.append(im_data)

    train_csv_path = "data/csv/train/all.csv"
    Region2Csv.combine_csv(csv_paths, train_csv_path)
    rf_simi = RandomForest()
    rf_simi.train(train_csv_path)
    model_path = model_path_same_region
    rf_simi.save_model(model_path)

    for i, im_data in enumerate(img_datas):
        print("finished multi seg {}".format(i))
        im_data.get_multi_segs(rf_simi)
        csv_temp_paths = []
        for j, rlist in enumerate(im_data.rlists):
            temp_path = "data/csv/temp{}.csv".format(j)
            csv_temp_paths.append(temp_path)
            Region2Csv.generate_seg_csv(
                rlist, im_data.feature93s[j], seg_paths[i], temp_path
            )
        Region2Csv.combine_csv(csv_temp_paths, seg_csv_paths[i])

    train_csv_path = "data/csv/train/seg_all.csv"
    Region2Csv.combine_csv(seg_csv_paths, train_csv_path)
    rf_sal = RandomForest()
    rf_sal.train(train_csv_path)
    model_path = model_path_salience
    rf_sal.save_model(model_path)

    ground_truths = []
    salience_maps = []
    for i, im_data in enumerate(img_datas):
        print("finish w {}".format(i))
        segs_num = len(im_data.rlists)
        if segs_num < len(C_LIST) + 1:
            continue
        height = im_data.rmat.shape[0]
        width = im_data.rmat.shape[1]
        salience_map = np.zeros([segs_num, height, width])
        for j, rlist in enumerate(im_data.rlists):
            Y = rf_sal.predict(im_data.feature93s[j])[:, 1]
            for k, r in enumerate(rlist):
                salience_map[j][r] = Y[k]
        ground_truth = cv2.imread(seg_paths[i])[:, :, 0]
        ground_truth[ground_truth == 255] = 1
        salience_maps.append(salience_map.reshape([-1, height * width]).T)
        ground_truths.append(ground_truth.reshape(-1))

    # mlp = MLP()
    # X_train = np.array(salience_maps)
    # X_train = np.concatenate(X_train, axis=0)
    # Y_train = np.array(ground_truths)
    # Y_train = np.concatenate(Y_train, axis=0)
    # mlp.train(X_train, Y_train)
    # model_path = "data/model/mlp.pkl"
    # mlp.save_model(model_path)

    # xgb = XGB()
    # X_train = np.array(salience_maps)
    # X_train = np.concatenate(X_train, axis=0)
    # Y_train = np.array(ground_truths)
    # Y_train = np.concatenate(Y_train, axis=0)
    # xgb.train(X_train, Y_train)
    # model_path = "data/model/xgb.pkl"
    # xgb.save_model(model_path)

    fusion_model = get_fusion_model(fm)
    X_train = np.array(salience_maps)
    X_train = np.concatenate(X_train, axis=0)
    Y_train = np.array(ground_truths)
    Y_train = np.concatenate(Y_train, axis=0)
    fusion_model.train(X_train, Y_train)
    fusion_model.save_model(model_path_fusion)
