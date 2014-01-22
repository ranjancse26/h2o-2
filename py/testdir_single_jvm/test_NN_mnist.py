import unittest, time, sys, random, string
sys.path.extend(['.','..','py'])
import h2o, h2o_gbm, h2o_nn, h2o_cmd, h2o_glm, h2o_hosts, h2o_import as h2i, h2o_jobs, h2o_browse as h2b

class Basic(unittest.TestCase):
    def tearDown(self):
        h2o.check_sandbox_for_errors()

    @classmethod
    def setUpClass(cls):
        localhost = h2o.decide_if_localhost()
        if (localhost):
            h2o.build_cloud(1, java_heap_GB=10, base_port=54323)
        else:
            h2o_hosts.build_cloud_with_hosts(base_port=54323)

    @classmethod
    def tearDownClass(cls):
        ###h2o.sleep(3600)
        h2o.tear_down_cloud()

    def test_NN_mnist_1(self):
        #h2b.browseTheCloud()
        h2o.beta_features = True
        csvPathname_train = 'mnist/train.csv.gz'
        csvPathname_test  = 'mnist/test.csv.gz'
        hex_key = 'mnist_train.hex'
        validation_key = 'mnist_test.hex'
        parseResult  = h2i.import_parse(bucket='smalldata', path=csvPathname_train, schema='local', hex_key=hex_key, timeoutSecs=10)
        parseResultV = h2i.import_parse(bucket='smalldata', path=csvPathname_test, schema='local', hex_key=validation_key, timeoutSecs=30)
        inspect = h2o_cmd.runInspect(None, parseResult['destination_key'])
        print "\n" + csvPathname_train, \
            "    numRows:", "{:,}".format(inspect['numRows']), \
            "    numCols:", "{:,}".format(inspect['numCols'])

        modes = [
            'SingleThread', 
            'SingleNode',
            #'MapReduce'
            ]

        for mode in modes:

            #Making random id
            identifier = ''.join(random.sample(string.ascii_lowercase + string.digits, 10))
            model_key = 'nn_' + identifier + '.hex'

            kwargs = {
                'ignored_cols'                 : None,
                'response'                     : '784',
                'mode'                         : mode,
                'activation'                   : 'RectifierWithDropout',
                'input_dropout_ratio'          : 0.2,
                'hidden'                       : '117,131,129',
                'rate'                         : 0.005,
                'rate_annealing'               : 1e-6,
                'momentum_start'               : 0.5,
                'momentum_ramp'                : 100000,
                'momentum_stable'              : 0.9,
                'l1'                           : 0.00001,
                'l2'                           : 0.0000001,
                'seed'                         : 98037452452,
                'loss'                         : 'CrossEntropy',
                'max_w2'                       : 15,
                'warmup_samples'               : 0,
                'initial_weight_distribution'  : 'UniformAdaptive',
                #'initial_weight_scale'         : 0.01,
                'epochs'                       : 2.0,
                'destination_key'              : model_key,
                'validation'                   : validation_key,
            }
            expectedErr = 0.0655 ## expected validation error for the above model

            timeoutSecs = 60
            start = time.time()
            nnResult = h2o_cmd.runNNet(parseResult=parseResult, timeoutSecs=timeoutSecs, noPoll=True, **kwargs)
            h2o.verboseprint("\nnnResult:", h2o.dump_json(nnResult))
            h2o_jobs.pollWaitJobs(pattern=None, timeoutSecs=timeoutSecs, pollTimeoutSecs=10, retryDelaySecs=5)
            print "neural net end on ", csvPathname_train, " and ", csvPathname_test, 'took', time.time() - start, 'seconds'
            modelView = h2o_cmd.runNeuralView(model_key=model_key)

            relTol = 0.02 if mode == 'SingleThread' else 0.05 ### 5% relative error is acceptable for Hogwild
            h2o_nn.simpleCheckValidationError(self, modelView, inspect['numRows'], expectedErr, relTol, **kwargs)

            h2o.beta_features = False

if __name__ == '__main__':
    h2o.unit_main()
