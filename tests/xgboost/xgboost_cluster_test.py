import random

import numpy as np
from pyspark.ml.linalg import Vectors

from sparkdl.xgboost import XgboostClassifier, XgboostRegressor
from tests.tests import SparkDLClusterTestCase
import json


class XgboostMainClusterTestCase(SparkDLClusterTestCase):

    def _get_max_num_concurrent_tasks(self, sc):
        """Gets the current max number of concurrent tasks."""
        # spark 3.1 and above has a different API for fetching max concurrent tasks
        if sc._jsc.sc().version() >= '3.1':
            return sc._jsc.sc().maxNumConcurrentTasks(
                sc._jsc.sc().resourceProfileManager().resourceProfileFromId(0)
            )
        return sc._jsc.sc().maxNumConcurrentTasks()

    def setUp(self):
        random.seed(2020)
        self.session.sparkContext.parallelize(list(range(4)), 4).collect()
        self.n_workers = self._get_max_num_concurrent_tasks(self.session.sparkContext)

        # Distributed section
        # Binary classification
        self.cls_df_train_distributed = self.session.createDataFrame([
                (Vectors.dense(1.0, 2.0, 3.0), 0),
                (Vectors.sparse(3, {1: 1.0, 2: 5.5}), 1),
                (Vectors.dense(4.0, 5.0, 6.0), 0),
                (Vectors.sparse(3, {1: 6.0, 2: 7.5}), 1),
            ] * 100, ["features", "label"])
        self.cls_df_test_distributed = self.session.createDataFrame([
            (Vectors.dense(1.0, 2.0, 3.0), 0, [0.9949826, 0.0050174]),
            (Vectors.sparse(3, {1: 1.0, 2: 5.5}), 1, [0.0050174, 0.9949826]),
            (Vectors.dense(4.0, 5.0, 6.0), 0, [0.9949826, 0.0050174]),
            (Vectors.sparse(3, {1: 6.0, 2: 7.5}), 1, [0.0050174, 0.9949826]),
            ], ["features", "expected_label", "expected_probability"])
        # Binary classification with different num_estimators
        self.cls_df_test_distributed_lower_estimators = self.session.createDataFrame([
            (Vectors.dense(1.0, 2.0, 3.0), 0, [0.9735, 0.0265]),
            (Vectors.sparse(3, {1: 1.0, 2: 5.5}), 1, [0.0265, 0.9735]),
            (Vectors.dense(4.0, 5.0, 6.0), 0, [0.9735, 0.0265]),
            (Vectors.sparse(3, {1: 6.0, 2: 7.5}), 1, [0.0265 , 0.9735]),
            ], ["features", "expected_label", "expected_probability"])

        # Multiclass classification
        self.cls_df_train_distributed_multiclass = self.session.createDataFrame([
                (Vectors.dense(1.0, 2.0, 3.0), 0),
                (Vectors.sparse(3, {1: 1.0, 2: 5.5}), 1),
                (Vectors.dense(4.0, 5.0, 6.0), 0),
                (Vectors.sparse(3, {1: 6.0, 2: 7.5}), 2),
            ] * 100, ["features", "label"])
        self.cls_df_test_distributed_multiclass = self.session.createDataFrame([
            (Vectors.dense(1.0, 2.0, 3.0), 0, [ 4.294563,  -2.449409,  -2.449409 ]),
            (Vectors.sparse(3, {1: 1.0, 2: 5.5}), 1, [-2.3796105,  3.669014,  -2.449409 ]),
            (Vectors.dense(4.0, 5.0, 6.0), 0, [ 4.294563,  -2.449409,  -2.449409 ]),
            (Vectors.sparse(3, {1: 6.0, 2: 7.5}), 2, [-2.3796105, -2.449409,   3.669014 ]),
            ], ["features", "expected_label", "expected_margins"])

        # Regression
        self.reg_df_train_distributed = self.session.createDataFrame([
                (Vectors.dense(1.0, 2.0, 3.0), 0),
                (Vectors.sparse(3, {1: 1.0, 2: 5.5}), 1),
                (Vectors.dense(4.0, 5.0, 6.0), 0),
                (Vectors.sparse(3, {1: 6.0, 2: 7.5}), 2),
            ] * 100, ["features", "label"])
        self.reg_df_test_distributed = self.session.createDataFrame([
            (Vectors.dense(1.0, 2.0, 3.0), 1.533e-04),
            (Vectors.sparse(3, {1: 1.0, 2: 5.5}), 9.999e-01),
            (Vectors.dense(4.0, 5.0, 6.0), 1.533e-04),
            (Vectors.sparse(3, {1: 6.0, 2: 7.5}), 1.999e+00),
            ], ["features", "expected_label"])

        # Adding weight and validation
        self.clf_params_with_eval_dist = {'validationIndicatorCol': 'isVal','early_stopping_rounds': 1, 'eval_metric': 'logloss'}
        self.clf_params_with_weight_dist = {'weightCol': 'weight'}
        self.cls_df_train_distributed_with_eval_weight = self.session.createDataFrame([
                (Vectors.dense(1.0, 2.0, 3.0), 0, False, 1.0),
                (Vectors.sparse(3, {1: 1.0, 2: 5.5}), 1, False, 2.0),
                (Vectors.dense(4.0, 5.0, 6.0), 0, True, 1.0),
                (Vectors.sparse(3, {1: 6.0, 2: 7.5}), 1, True, 2.0),
            ] * 100, ["features", "label", "isVal", "weight"])
        self.cls_df_test_distributed_with_eval_weight = self.session.createDataFrame([
            (Vectors.dense(1.0, 2.0, 3.0), [0.9955, 0.0044], [0.9904, 0.0096], [0.9903, 0.0097]),
        ], ["features", "expected_prob_with_weight", "expected_prob_with_eval",
            "expected_prob_with_weight_and_eval"])
        self.clf_best_score_eval = 0.009677
        self.clf_best_score_weight_and_eval = 0.006628

        self.reg_params_with_eval_dist = {'validationIndicatorCol': 'isVal','early_stopping_rounds': 1, 'eval_metric': 'rmse'}
        self.reg_params_with_weight_dist = {'weightCol': 'weight'}
        self.reg_df_train_distributed_with_eval_weight = self.session.createDataFrame([
                (Vectors.dense(1.0, 2.0, 3.0), 0, False, 1.0),
                (Vectors.sparse(3, {1: 1.0, 2: 5.5}), 1, False, 2.0),
                (Vectors.dense(4.0, 5.0, 6.0), 0, True, 1.0),
                (Vectors.sparse(3, {1: 6.0, 2: 7.5}), 1, True, 2.0),
            ] * 100, ["features", "label", "isVal", "weight"])
        self.reg_df_test_distributed_with_eval_weight = self.session.createDataFrame([
            (Vectors.dense(1.0, 2.0, 3.0), 4.583e-05, 5.239e-05, 6.03e-05),
            (Vectors.sparse(3, {1: 1.0, 2: 5.5}), 9.9997e-01, 9.99947e-01, 9.9995e-01)
        ], ["features", "expected_prediction_with_weight", "expected_prediction_with_eval",
            "expected_prediction_with_weight_and_eval"])
        self.reg_best_score_eval = 5.2e-05
        self.reg_best_score_weight_and_eval = 4.9e-05

    def test_classifier_distributed_basic(self):
        classifier = XgboostClassifier(num_workers=self.n_workers, n_estimators=100, use_external_storage=False)
        model = classifier.fit(self.cls_df_train_distributed)
        pred_result = model.transform(self.cls_df_test_distributed).collect()
        for row in pred_result:
            self.assertTrue(np.isclose(row.expected_label,
                                        row.prediction, atol=1e-3))
            self.assertTrue(np.allclose(row.expected_probability, row.probability, atol=1e-3))

    def test_classifier_distributed_external_storage_basic(self):
        classifier = XgboostClassifier(num_workers=self.n_workers, n_estimators=100, use_external_storage=True)
        model = classifier.fit(self.cls_df_train_distributed)
        pred_result = model.transform(self.cls_df_test_distributed).collect()
        for row in pred_result:
            self.assertTrue(np.isclose(row.expected_label,
                                        row.prediction, atol=1e-3))
            self.assertTrue(np.allclose(row.expected_probability, row.probability, atol=1e-3))

    def test_classifier_distributed_multiclass(self):
        # There is no built-in multiclass option for external storage
        classifier = XgboostClassifier(num_workers=self.n_workers, n_estimators=100, use_external_storage=False)
        model = classifier.fit(self.cls_df_train_distributed_multiclass)
        pred_result = model.transform(self.cls_df_test_distributed_multiclass).collect()
        for row in pred_result:
            self.assertTrue(np.isclose(row.expected_label,
                                        row.prediction, atol=1e-3))
            self.assertTrue(np.allclose(row.expected_margins, row.rawPrediction, atol=1e-3))

    def test_regressor_distributed_basic(self):
        regressor = XgboostRegressor(num_workers=self.n_workers, n_estimators=100, use_external_storage=False)
        model = regressor.fit(self.reg_df_train_distributed)
        pred_result = model.transform(self.reg_df_test_distributed).collect()
        for row in pred_result:
            self.assertTrue(np.isclose(row.expected_label,
                                        row.prediction, atol=1e-3))

    def test_regressor_distributed_external_storage_basic(self):
        regressor = XgboostRegressor(num_workers=self.n_workers, n_estimators=100, use_external_storage=True)
        model = regressor.fit(self.reg_df_train_distributed)
        pred_result = model.transform(self.reg_df_test_distributed).collect()
        for row in pred_result:
            self.assertTrue(np.isclose(row.expected_label,
                                        row.prediction, atol=1e-3))

    def check_use_gpu_param(self):
        # Classifier
        classifier = XgboostClassifier(num_workers=self.n_workers, n_estimators=100, use_gpu=True, use_external_storage=False)
        self.assertTrue(hasattr(classifier, 'use_gpu'))
        self.assertTrue(classifier.getOrDefault(classifier.use_gpu))
        clf_model = classifier.fit(self.cls_df_train_distributed)
        pred_result = model.transform(self.cls_df_test_distributed).collect()
        for row in pred_result:
            self.assertTrue(np.isclose(row.expected_label,
                                        row.prediction, atol=1e-3))
            self.assertTrue(np.allclose(row.expected_probability, row.probability, atol=1e-3))
        
        regressor = XgboostRegressor(num_workers=self.n_workers, n_estimators=100, use_gpu=True, use_external_storage=False)
        self.assertTrue(hasattr(regressor, 'use_gpu'))
        self.assertTrue(regressor.getOrDefault(regressor.use_gpu))
        model = regressor.fit(self.reg_df_train_distributed)
        pred_result = model.transform(self.reg_df_test_distributed).collect()
        for row in pred_result:
            self.assertTrue(np.isclose(row.expected_label,
                                        row.prediction, atol=1e-3))

    def test_classifier_distributed_weight_eval(self):
        # with weight
        classifier = XgboostClassifier(num_workers=self.n_workers, n_estimators=100, use_external_storage=False, **self.clf_params_with_weight_dist)
        model = classifier.fit(self.cls_df_train_distributed_with_eval_weight)
        pred_result = model.transform(self.cls_df_test_distributed_with_eval_weight).collect()
        for row in pred_result:
            self.assertTrue(np.allclose(row.probability,
                                        row.expected_prob_with_weight, atol=1e-3))

        # with eval only
        classifier = XgboostClassifier(num_workers=self.n_workers, n_estimators=100, use_external_storage=False, **self.clf_params_with_eval_dist)
        model = classifier.fit(self.cls_df_train_distributed_with_eval_weight)
        pred_result = model.transform(self.cls_df_test_distributed_with_eval_weight).collect()
        for row in pred_result:
            self.assertTrue(np.allclose(row.probability,
                                        row.expected_prob_with_eval, atol=1e-3))
        self.assertEqual(float(model.get_booster().attributes()["best_score"]), self.clf_best_score_eval)

        # with both weight and eval
        classifier = XgboostClassifier(num_workers=self.n_workers, n_estimators=100, use_external_storage=False, **self.clf_params_with_eval_dist, **self.clf_params_with_weight_dist)
        model = classifier.fit(self.cls_df_train_distributed_with_eval_weight)
        pred_result = model.transform(self.cls_df_test_distributed_with_eval_weight).collect()
        for row in pred_result:
            self.assertTrue(np.allclose(row.probability,
                                        row.expected_prob_with_weight_and_eval, atol=1e-3))
        self.assertEqual(float(model.get_booster().attributes()["best_score"]), self.clf_best_score_weight_and_eval)

    def test_classifier_distributed_weight_eval_external_storage(self):
        # with weight
        classifier = XgboostClassifier(num_workers=self.n_workers, n_estimators=100, use_external_storage=True, **self.clf_params_with_weight_dist)
        model = classifier.fit(self.cls_df_train_distributed_with_eval_weight)
        pred_result = model.transform(self.cls_df_test_distributed_with_eval_weight).collect()
        for row in pred_result:
            self.assertTrue(np.allclose(row.probability,
                                        row.expected_prob_with_weight, atol=1e-3))

        # with eval only
        classifier = XgboostClassifier(num_workers=self.n_workers, n_estimators=100, use_external_storage=True, **self.clf_params_with_eval_dist)
        model = classifier.fit(self.cls_df_train_distributed_with_eval_weight)
        pred_result = model.transform(self.cls_df_test_distributed_with_eval_weight).collect()
        for row in pred_result:
            self.assertTrue(np.allclose(row.probability,
                                        row.expected_prob_with_eval, atol=1e-3))
        self.assertEqual(float(model.get_booster().attributes()["best_score"]), self.clf_best_score_eval)

        # with both weight and eval
        classifier = XgboostClassifier(num_workers=self.n_workers, n_estimators=100, use_external_storage=True, **self.clf_params_with_eval_dist, **self.clf_params_with_weight_dist)
        model = classifier.fit(self.cls_df_train_distributed_with_eval_weight)
        pred_result = model.transform(self.cls_df_test_distributed_with_eval_weight).collect()
        for row in pred_result:
            self.assertTrue(np.allclose(row.probability,
                                        row.expected_prob_with_weight_and_eval, atol=1e-3))
        self.assertEqual(float(model.get_booster().attributes()["best_score"]), self.clf_best_score_weight_and_eval)

    def test_regressor_distributed_weight_eval(self):
        # with weight
        regressor = XgboostRegressor(num_workers=self.n_workers, n_estimators=100, use_external_storage=False, **self.reg_params_with_weight_dist)
        model = regressor.fit(self.reg_df_train_distributed_with_eval_weight)
        pred_result = model.transform(self.reg_df_test_distributed_with_eval_weight).collect()
        for row in pred_result:
            self.assertTrue(
                np.isclose(row.prediction,
                           row.expected_prediction_with_weight, atol=1e-3))
        # with eval only
        regressor = XgboostRegressor(num_workers=self.n_workers, n_estimators=100, use_external_storage=False, **self.reg_params_with_eval_dist)
        model = regressor.fit(self.reg_df_train_distributed_with_eval_weight)
        pred_result = model.transform(self.reg_df_test_distributed_with_eval_weight).collect()
        for row in pred_result:
            self.assertTrue(
                np.isclose(row.prediction,
                           row.expected_prediction_with_eval, atol=1e-3))
        self.assertEqual(float(model.get_booster().attributes()["best_score"]), self.reg_best_score_eval)
        # with both weight and eval
        regressor = XgboostRegressor(num_workers=self.n_workers, n_estimators=100, use_external_storage=False, **self.reg_params_with_eval_dist, **self.reg_params_with_weight_dist)
        model = regressor.fit(self.reg_df_train_distributed_with_eval_weight)
        pred_result = model.transform(self.reg_df_test_distributed_with_eval_weight).collect()
        for row in pred_result:
            self.assertTrue(
                np.isclose(row.prediction,
                           row.expected_prediction_with_weight_and_eval, atol=1e-3))
        self.assertEqual(float(model.get_booster().attributes()["best_score"]), self.reg_best_score_weight_and_eval)

    def test_regressor_distributed_weight_eval_external_storage(self):
        # with weight
        regressor = XgboostRegressor(num_workers=self.n_workers, n_estimators=100, use_external_storage=True, **self.reg_params_with_weight_dist)
        model = regressor.fit(self.reg_df_train_distributed_with_eval_weight)
        pred_result = model.transform(self.reg_df_test_distributed_with_eval_weight).collect()
        for row in pred_result:
            self.assertTrue(
                np.isclose(row.prediction,
                           row.expected_prediction_with_weight, atol=1e-3))
        # with eval only
        regressor = XgboostRegressor(num_workers=self.n_workers, n_estimators=100, use_external_storage=True, **self.reg_params_with_eval_dist)
        model = regressor.fit(self.reg_df_train_distributed_with_eval_weight)
        pred_result = model.transform(self.reg_df_test_distributed_with_eval_weight).collect()
        for row in pred_result:
            self.assertTrue(
                np.isclose(row.prediction,
                           row.expected_prediction_with_eval, atol=1e-3))
        self.assertEqual(float(model.get_booster().attributes()["best_score"]), self.reg_best_score_eval)
        # with both weight and eval
        regressor = XgboostRegressor(num_workers=self.n_workers, n_estimators=100, use_external_storage=True, **self.reg_params_with_eval_dist, **self.reg_params_with_weight_dist)
        model = regressor.fit(self.reg_df_train_distributed_with_eval_weight)
        pred_result = model.transform(self.reg_df_test_distributed_with_eval_weight).collect()
        for row in pred_result:
            self.assertTrue(
                np.isclose(row.prediction,
                           row.expected_prediction_with_weight_and_eval, atol=1e-3))
        self.assertEqual(float(model.get_booster().attributes()["best_score"]), self.reg_best_score_weight_and_eval)

    def test_num_estimators(self):
        classifier = XgboostClassifier(num_workers=self.n_workers, n_estimators=10, use_external_storage=False)
        model = classifier.fit(self.cls_df_train_distributed)
        pred_result = model.transform(self.cls_df_test_distributed_lower_estimators).collect()
        print(pred_result)
        for row in pred_result:
            self.assertTrue(np.isclose(row.expected_label,
                                        row.prediction, atol=1e-3))
            self.assertTrue(np.allclose(row.expected_probability, row.probability, atol=1e-3))

    def test_missing_value_zero_with_external_storage(self):
        classifier = XgboostClassifier(num_workers=self.n_workers, n_estimators=10, use_external_storage=False,
                                       missing=0.0)
        classifier.fit(self.cls_df_train_distributed)

    def test_distributed_params(self):
        classifier = XgboostClassifier(num_workers=self.n_workers, max_depth=7)
        model = classifier.fit(self.cls_df_train_distributed)
        self.assertTrue(hasattr(classifier, 'max_depth'))
        self.assertEqual(classifier.getOrDefault(classifier.max_depth), 7)
        booster_config = json.loads(model.get_booster().save_config())
        max_depth = booster_config["learner"]["gradient_booster"]["updater"]["grow_histmaker"]["train_param"]["max_depth"]
        self.assertEqual(int(max_depth), 7)

    def test_repartition(self):
        # The following test case has a few partitioned datasets that are either
        # well partitioned relative to the number of workers that the user wants
        # or poorly partitioned. We only want to repartition when the dataset
        # is poorly partitioned so _repartition_needed is true in those instances.

        classifier = XgboostClassifier(num_workers=self.n_workers)
        basic = self.cls_df_train_distributed
        self.assertTrue(classifier._repartition_needed(basic))
        bad_repartitioned = basic.repartition(self.n_workers + 1)
        self.assertTrue(classifier._repartition_needed(bad_repartitioned))
        good_repartitioned = basic.repartition(self.n_workers)
        self.assertFalse(classifier._repartition_needed(good_repartitioned))

        # Now testing if force_repartition returns True regardless of whether the data is well partitioned
        classifier = XgboostClassifier(num_workers=self.n_workers, force_repartition=True)
        good_repartitioned = basic.repartition(self.n_workers)
        self.assertTrue(classifier._repartition_needed(good_repartitioned))
