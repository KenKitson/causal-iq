
#   Core code for running learning experiments

import pytest
from pandas import set_option
from time import localtime, asctime

from core.common import Randomise
from fileio.common import EXPTS_DIR
from fileio.pandas import Pandas
from fileio.oracle import Oracle
from call.bnlearn import bnlearn_learn
from call.tetrad import tetrad_learn
from learn.hc import hc
from learn.trace import Trace
from learn.knowledge import Knowledge
from experiments.common import series_props, reference_bn, \
    Algorithm, Package, process_args, Ordering


@pytest.fixture()
def args(pytestconfig):
    args = {'action': pytestconfig.getoption("action"),
            'series': pytestconfig.getoption('series'),
            'networks': pytestconfig.getoption('networks'),
            'N': pytestconfig.getoption('N')}
    return args


def do_experiment(action, series, network, N, existing, props, bn, data,
                  context, randomise, sample_num, root_dir=EXPTS_DIR,
                  init_cache=True):
    """
        Run an individual learning experiment.

        :param str action: skip, check or replace any existing trace
        :param str series: series to which experiment belongs
        :param str network: network used for experiment
        :param int N: sample size to use
        :param dict existing: existing traces {key: trace}
        :param dict props: properties of the series
        :param BN bn: reference BN for network
        :param Data data: data to learn structure from
        :param dict context: context structure for this experiment
        :param list/None randomise: list of Randomise to be randomised
        :param int sample_num: sample number
        :param bool init_cache: whether to initialise the score cache

        :returns tuple: diffs: bool/None, whether trace same as any previous
                        trace: Trace for this experiment
    """
    params = props['params']
    package = props['package']

    #   Determine key for this sample size and see if it has already been
    #   performed and so can be skipped if action is "skip"

    key = ("N{}".format(N) if len(randomise) == 0
           else "N{}_{}".format(N, sample_num))
    if action == 'skip' and key in existing:
        print('  {} with key {} ... skipping ...'.format(network, key))
        return (False, None)

    #   Determine id for this experiment

    print('  learning {} for sample {} at {} ...'
          .format(network, key, asctime(localtime())))
    context.update({'id': '{}/{}/{}'.format(series, network, key),
                    'randomise': randomise})

    # set the sample size, and optionally randomise row order

    seed = (sample_num if Randomise.ROWS in randomise
            and props['datagen'] != 'none' else None)
    data.set_N(N, seed)
    if seed is not None:
        print('\nTop 5 random rows:\n{}'.format(data.sample.head()))

    # construct and score sample for true DAG - only for for sample 0

    if (props['datagen'] != 'none' and 'score' in props['params']
            and sample_num == -1):
        type = props['params']['score']
        score = bn.dag.score(data=data, types=type,
                             params={'k': 1, 'unistate_ok': True})
        score = round(score[type].sum() / N, 5)
        print('  true graph normalised {} score for sample {} is {}'
              .format(type, key, score))
        context.update({'score': score})

    # randomise node names if necessary

    if Randomise.NAMES in randomise:
        data.randomise_names(seed=sample_num)

    #   Set the node processing order

    if props['ordering'] in {Ordering.OPTIMAL, Ordering.WORST}:
        order = [n for n in bn.dag.ordered_nodes()]
        order = order[::-1] if props['ordering'] == Ordering.WORST else order
        data.set_order(order=tuple(order))
    elif Randomise.ORDER in randomise:
        data.randomise_order(seed=sample_num)
    nodes = list(data.get_order())
    context.update({'var_order': nodes})
    print('  variable order is: {}{}'
          .format(', '.join(nodes[:10]), '' if len(nodes) <= 10 else ' ...'))

    if props['datagen'] == 'none':

        # Oracle learning from CPTs - only bnbench HC supports this

        if package != Package.BNBENCH or props['algorithm'] != Algorithm.HC:
            raise ValueError('Oracle learning only possible for bnbench HC')
        _, trace = hc(data=data, params=params, context=context)

    elif package == Package.BNBENCH:

        # bnbench's implementation of HC

        if props['knowledge'] is not False:
            kparams = ({} if props['kparams'] is None
                       else props['kparams'].copy())
            kparams.update({'ref': bn})
            knowledge = Knowledge(rules=props['knowledge'], params=kparams,
                                  sample=sample_num)
        else:
            knowledge = False
        if props['algorithm'] != Algorithm.HC:
            raise ValueError('bnbench only supports HC algorithm')
        _, trace = hc(data=data, params=params, context=context,
                      knowledge=knowledge, init_cache=init_cache)

    elif package == Package.TETRAD:

        # Tetrad algorithm

        try:
            _, trace = tetrad_learn(props['algorithm'].value['method'],
                                    data.sample, params=params,
                                    context=context, dstype=data.dstype)
        except RuntimeError:
            print('*** tetrad failed to learn graph')
            return (None, False)
    else:

        # bnlearn algorithm

        try:
            _, trace = bnlearn_learn(props['algorithm'].value['method'],
                                     data.sample, params=params,
                                     context=context, dstype=data.dstype)
        except RuntimeError:
            print('*** bnlearn failed to learn graph')
            return (None, False)

    print('  learnt in {} seconds at {}\n'
          .format(round(trace.trace['time'][-1], 2), asctime(localtime())))

    if Randomise.NAMES in randomise:
        trace.rename(name_map=data.ext_to_orig)

    if key in existing and action == 'compare':

        # Re-running an experiment - check it strictly gives same result.

        diffs = trace.diffs_from(existing[key], strict=True)
        if diffs is not None:
            print('\nRerun differences\n{}\n\npreviously:\n{}\n\nnow:\n{}'
                  .format(diffs[2], existing[key], trace))
            if diffs[0] == {}:
                print('Minor differences at {}'.format(diffs[1]))
            diffs = True
        else:
            diffs = False
    else:
        trace.save(root_dir)  # save this new result
        diffs = None

    return (diffs, trace)


def run_learn(args, root_dir=EXPTS_DIR):
    """
        General entry point to running learning algorithms completely
        controlled by command line arguments. Very flexible but won't
        be parallelised.

        :param dict args: relevant command line arguments {name: value}:
                            - action: skip/compare/replace previous result
                            - series: series to run e.g. HC_N_1
                            - networks: networks to use e.g. 'asia,cancer'
                            - N: range of sample sizes, e.g. 100,2000
        :param str root_dir: root location of files

        :raises TypeError: if bad arg types
        :raises ValueError: if bad arg values

        :returns boolean: whether all experiments succeeded
    """
    if not isinstance(args, dict) or not isinstance(root_dir, str):
        raise TypeError('run_learn() bad arg types')

    action, reqd_series, _, networks, _, Ns, Ss, _, _, _ = \
        process_args(args, analyse=False)
    if action is None:
        if root_dir != EXPTS_DIR:
            raise ValueError('run_learn() bad arg values')
        return

    set_option('display.max_rows', None)
    set_option('display.max_columns', None)
    set_option('display.width', None)

    for series in reqd_series:

        # Determine the properties for this series

        props = series_props(series)
        print('\n\nSeries {} has properties: {}'.format(series, props))

        for network in networks:

            # Determine which experiments already done, and so if there are any
            # experiments to do (--action=compare/skip redoes them)

            existing = Trace.read(series + '/' + network, root_dir)
            existing = existing if existing else {}

            #   Get BN for network

            ref_bn, bn_file = reference_bn(network, root_dir)
            context = {'in': bn_file}

            #   If learning from data, generate with largest sample size

            if props['datagen'] != 'none':
                dstype = ('continuous' if network.endswith('_c')
                          else 'categorical')
                if ('params' in props and 'score' in props['params']
                    and props['params']['score'] == 'bic'
                        and dstype == 'continuous'):
                    props['params']['score'] = 'bic-g'
                if ('params' in props and 'test' in props['params']
                    and props['params']['test'] == 'mi'
                        and dstype == 'continuous'):
                    props['params']['test'] = 'mi-g'
                data = Pandas.read(root_dir + '/datasets/' + network +
                                   '.data.gz', dstype=dstype, N=Ns[-1])
            else:
                print('\nLearning from distribution (oracle)')
                data = Oracle(bn=ref_bn)

            # Determine if random sampling of data or order is to be performed

            if props['randomise'] is False:
                num_samples = 1
                randomise = []
            else:
                num_samples = props['randomise'][1]
                randomise = props['randomise'][0]

            # Loop over dataset sizes and any randomisation samples at each
            # set size

            print('\nLearning {} for N from {} to {} ({} samples per N)...\n'
                  .format(network, Ns[0], Ns[-1], num_samples))
            all_ok = True
            for N in Ns:
                init_cache = True  # cache values depend upon sample size
                for i in range(num_samples):
                    if Ss is not None and (i < Ss[0] or i > Ss[1]):
                        continue
                    diffs, trace = \
                        do_experiment(action, series, network, N, existing,
                                      props, ref_bn, data, context,
                                      randomise, i, root_dir, init_cache)
                    if trace is not None and Randomise.NAMES not in randomise:
                        init_cache = False
                    if diffs is not False:
                        print(diffs)
                        all_ok = False

    return all_ok