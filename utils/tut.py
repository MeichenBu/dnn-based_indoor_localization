#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
# @file     tut.py
# @author   Kyeong Soo (Joseph) Kim <kyeongsoo.kim@gmail.com>
# @date     2018-07-24
#
# @brief A parser and preprocessor for the TUT Wi-Fi fingerprinting
#        dataset.
#
# @remarks For details of the TUT dataset, please refer [1].
#
#          [1] E. S. Lohan et al., "Wi-Fi crowdsourced fingerprinting dataset
#          for indoor positioning," Data, vol. 2, no. 4, article no. 32,
#          pp. 1-16, 2017. 

### import basic modules and a model to test
import os
import sys
### import other modules; keras and its backend will be loaded later
import cloudpickle  # for storing namedtuples
import numpy as np
import pandas as pd
import pathlib
from collections import namedtuple


class TUT(object):
    def __init__(self,
                 path='.',
                 cache=False,
                 frac=1.0,
                 preprocessor='standard_scaler',
                 classification_mode='hierarchical',
                 lack_of_ap=-110):
        self.training_rss_fname = path + '/' + 'Training_rss_21Aug17.csv'  # RSS=100 for lack of AP
        self.training_coords_fname = path + '/' + 'Training_coordinates_21Aug17.csv'  # 3-D coordinates in meters
        self.testing_rss_fname = path + '/' + 'Test_rss_21Aug17.csv'  # RSS=100 for lack of AP
        self.testing_coords_fname = path + '/' + 'Test_coordinates_21Aug17.csv'  # 3-D coordinates in meters
        self.cache = cache
        self.frac = frac
        if preprocessor == 'standard_scaler':
            from sklearn.preprocessing import StandardScaler
            self.rss_scaler = StandardScaler()
            self.coord_scaler = StandardScaler()
        elif preprocessor == 'minmax_scaler':
            from sklearn.preprocessing import MinMaxScaler
            self.rss_scaler = MinMaxScaler()
            self.coord_scaler = MinMaxScaler()
        elif preprocessor == 'normalizer':
            from sklearn.preprocessing import Normalizer
            self.rss_scaler = Normalizer()
            self.coord_scaler = Normalizer()
        else:
            print("{0:s} preprocessor is not supported.".format(preprocessor))
            sys.exit()
        self.classification_mode = classification_mode
        self.lack_of_ap = lack_of_ap
        self.saved_fname = path + '/saved/tut' + '_F{0:.1f}_L{1:d}_P{2:s}.cpkl'.format(
            frac, lack_of_ap,
            preprocessor)  # cloudpickle file name for saved objects

    def load_data(self):
        if self.cache == True and os.path.isfile(self.saved_fname) and (os.path.getmtime(
                self.saved_fname) > os.path.getmtime(__file__)):
            with open(self.saved_fname, 'rb') as input_file:
                self.training_df = cloudpickle.load(input_file)
                self.training_data = cloudpickle.load(input_file)
                self.testing_df = cloudpickle.load(input_file)
                self.testing_data = cloudpickle.load(input_file)
        else:
            rss_df = (pd.read_csv(
                self.training_rss_fname, header=None)).sample(
                    frac=self.frac
                )
            num_aps = rss_df.shape[1]
            rss_df.columns = np.char.array(np.repeat('WAP', num_aps)) + np.char.array(range(num_aps), unicode=True)
            coords_df = (pd.read_csv(
                self.training_coords_fname, header=None)).sample(
                    frac=self.frac
                )
            coords_df.columns = ['X', 'Y', 'Z']
            self.training_df = pd.concat([rss_df, coords_df], axis=1, join_axes=[rss_df.index])
            self.training_df['FLOOR'] = (round(self.training_df['Z'] / 3.7)).astype(int)  # 3.7 is the floor height
            self.training_df['BUILDINGID'] = 0
            
            rss_df = (pd.read_csv(
                self.testing_rss_fname, header=None)).sample(
                    frac=self.frac
                )
            num_aps = rss_df.shape[1]
            rss_df.columns = np.char.array(np.repeat('WAP', num_aps)) + np.char.array(range(num_aps), unicode=True)
            coords_df = (pd.read_csv(
                self.testing_coords_fname, header=None)).sample(
                    frac=self.frac
                )
            coords_df.columns = ['X', 'Y', 'Z']
            self.testing_df = pd.concat([rss_df, coords_df], axis=1, join_axes=[rss_df.index])
            self.testing_df['FLOOR'] = (round(self.testing_df['Z'] / 3.7)).astype(int)  # 3.7 is the floor height
            self.testing_df['BUILDINGID'] = 0

            # # merge training and testing datasets into one
            # self.tut_df = pd.concat([self.testing_df, self.training_df])
            
            # process RSS
            # N.B. double precision needed for proper working with scaler
            training_rss = np.asarray(
                self.training_df.iloc[:, :num_aps], dtype=np.float)
            training_rss[training_rss ==
                         100] = self.lack_of_ap  # RSS value for lack of AP
            testing_rss = np.asarray(self.testing_df.iloc[:, :num_aps], dtype=np.float)
            testing_rss[testing_rss ==
                        100] = self.lack_of_ap  # RSS value for lack of AP
            if self.rss_scaler != None:
                # scale over flattened data for joint scaling
                training_rss_scaled = (self.rss_scaler.fit_transform(
                    training_rss.reshape((-1, 1)))).reshape(
                        training_rss.shape)
                testing_rss_scaled = (self.rss_scaler.transform(
                    testing_rss.reshape(
                        (-1, 1)))).reshape(testing_rss.shape)  # scaled version
            else:
                training_rss_scaled = training_rss
                testing_rss_scaled = testing_rss

            # process local coordinates
            training_coord_x = np.asarray(
                self.training_df['X'], dtype=np.float)
            training_coord_y = np.asarray(
                self.training_df['Y'], dtype=np.float)
            training_coord = np.column_stack((training_coord_x, training_coord_y))
            num_coords = training_coord.shape[1]
            testing_coord_x = np.asarray(
                self.testing_df['X'], dtype=np.float)
            testing_coord_y = np.asarray(
                self.testing_df['Y'], dtype=np.float)
            testing_coord = np.column_stack((testing_coord_x, testing_coord_y))
            if self.coord_scaler != None:
                training_coord_scaled = self.coord_scaler.fit_transform(
                    training_coord)
                testing_coord_scaled = self.coord_scaler.transform(
                    testing_coord)  # scaled version
            else:
                training_coord_scaled = training_coord
                testing_coord_scaled = testing_coord

            # map locations (reference points) to sequential IDs per building &
            # floor before building labels
            self.training_df['REFPOINT'] = self.training_df.apply(lambda row:
                                                        str(row['X']) + ':' +
                                                        str(row['Y']),
                                                        axis=1) # add a new column
            blds = np.unique(self.training_df[['BUILDINGID']])
            flrs = np.unique(self.training_df[['FLOOR']])
            training_coord_avg = {}

            for bld in blds:
                n_rfps = 0
                sum_x = sum_y = 0.0
                for flr in flrs:
                    # map reference points to sequential IDs per building-floor before building labels
                    cond = (self.training_df['BUILDINGID'] == bld) & (
                        self.training_df['FLOOR'] == flr)
                    if len(self.training_df.loc[cond]) > 0:
                        _, idx = np.unique(
                            self.training_df.loc[cond, 'REFPOINT'],
                            return_inverse=True
                        )  # refer to numpy.unique manual
                        self.training_df.loc[cond, 'REFPOINT'] = idx

                        # calculate the average coordinates of each building/floor
                        df = self.training_df.loc[cond, [
                            'REFPOINT', 'Y', 'X'
                        ]].drop_duplicates(subset='REFPOINT')
                        x = np.mean(df.loc[cond, 'Y'])
                        y = np.mean(df.loc[cond, 'X'])
                        training_coord_avg[str(bld) + '-' + str(flr)] = np.array(
                            (x, y))
                        n = len(df)
                        sum_x += n * x
                        sum_y += n * y
                        n_rfps += n

                # calculate the average coordinates of each building
                training_coord_avg[str(bld)] = np.array((sum_x / n_rfps,
                                                       sum_y / n_rfps))

            # build labels for sequential multi-class classification of a building, a floor, and a location (reference point)
            num_training_samples = len(self.training_df)
            num_testing_samples = len(self.testing_df)
            labels_bld = np.asarray(
                pd.get_dummies(
                    pd.concat([
                        self.training_df['BUILDINGID'],
                        self.testing_df['BUILDINGID']
                    ]))
            )  # for consistency in one-hot encoding for both dataframes
            labels_flr = np.asarray(
                pd.get_dummies(
                    pd.concat(
                        [self.training_df['FLOOR'],
                         self.testing_df['FLOOR']])))  # ditto
            training_labels_bld = labels_bld[:num_training_samples]
            training_labels_flr = labels_flr[:num_training_samples]
            testing_labels_bld = labels_bld[num_training_samples:]
            testing_labels_flr = labels_flr[num_training_samples:]
            training_labels_loc = np.asarray(
                pd.get_dummies(self.training_df['REFPOINT']))
            # BUILDINGID: 1
            # FLOOR: 5
            # REFPOINT: 226
            # multi-label labels: array of 19937 x 905

            if self.classification_mode == 'hierarchical':
                TrainingData = namedtuple('TrainingData', [
                    'rss', 'rss_scaled', 'rss_scaler', 'coord', 'coord_avg',
                    'coord_scaled', 'coord_scaler', 'labels'
                ])
                TrainingLabels = namedtuple('TrainingLabels',
                                            ['building', 'floor', 'location'])
                training_labels = TrainingLabels(
                    building=training_labels_bld,
                    floor=training_labels_flr,
                    location=training_labels_loc)
                training_data = TrainingData(
                    rss=training_rss,
                    rss_scaled=training_rss_scaled,
                    rss_scaler=self.rss_scaler,
                    coord=training_coord,
                    coord_avg=training_coord_avg,
                    coord_scaled=training_coord_scaled,
                    coord_scaler=self.coord_scaler,
                    labels=training_labels)

                TestingData = namedtuple(
                    'TestingData',
                    ['rss', 'rss_scaled', 'coord', 'coord_scaled', 'labels'])
                TestingLabels = namedtuple('TestingLabels',
                                           ['building', 'floor'])
                testing_labels = TestingLabels(
                    building=testing_labels_bld, floor=testing_labels_flr)
                testing_data = TestingData(
                    rss=testing_rss,
                    rss_scaled=testing_rss_scaled,
                    coord=testing_coord,
                    coord_scaled=testing_coord_scaled,
                    labels=testing_labels)

            self.training_data = training_data
            self.testing_data = testing_data

            if self.cache == True:
                pathlib.Path(os.path.dirname(self.saved_fname)).mkdir(
                    parents=True, exist_ok=True)
                with open(self.saved_fname, 'wb') as output_file:
                    cloudpickle.dump(self.training_df, output_file)
                    cloudpickle.dump(self.training_data, output_file)
                    cloudpickle.dump(self.testing_df, output_file)
                    cloudpickle.dump(self.testing_data, output_file)

        return self.training_df, self.training_data, self.testing_df, self.testing_data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-C",
        "--cache",
        help=
        "whether to load data from/save them to a cache; default is False",
        default=False,
        type=bool)
    parser.add_argument(
        "-F",
        "--frac",
        help=
        "fraction of input data to load for training and validation; default is 1.0",
        default=1.0,
        type=float)
    parser.add_argument(
        "-P",
        "--preprocessor",
        help=
        "preprocessor to scale/normalize input data before training and validation; default is 'standard_scaler'",
        default='standard_scaler',
        type=str)
    parser.add_argument(
        "-L",
        "--lack_of_ap",
        help="RSS value for indicating lack of AP; default is -110",
        default=-110,
        type=int)
    args = parser.parse_args()
    cache = args.cache
    frac = args.frac
    preprocessor = args.preprocessor
    lack_of_ap = args.lack_of_ap

    ### load dataset after scaling
    data_path = '../data/tut'
    print("Loading TUT data ...")
    tut = TUT(
        path='../data/tut',
        cache=cache,
        frac=frac,
        preprocessor=preprocessor,
        classification_mode='hierarchical',
        lack_of_ap=lack_of_ap)
    training_df, training_data, testing_df, testing_data = tut.load_data(
    )
