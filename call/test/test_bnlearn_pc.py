
#   Test calling the bnlearn PC-stable structure learning algorithm

import pytest

from core.common import EdgeType
from call.bnlearn import bnlearn_learn
from fileio.common import TESTDATA_DIR
from fileio.pandas import Pandas
from core.bn import BN
from learn.pc import sgs_skeleton
import testdata.example_pdags as ex_pdag


def test_bnlearn_pc_type_error_1():  # no arguments
    with pytest.raises(TypeError):
        bnlearn_learn()


def test_bnlearn_pc_type_error_2():  # only one argument
    with pytest.raises(TypeError):
        bnlearn_learn(32.23)
    with pytest.raises(TypeError):
        bnlearn_learn('pc.stable')


def test_bnlearn_pc_type_error_3():  # invalid types
    with pytest.raises(TypeError):
        bnlearn_learn(32.23, '/discrete/tiny/ab_cb.dsc')
    with pytest.raises(TypeError):
        bnlearn_learn('pc.stable', [1, 2])


def test_bnlearn_pc_filenotfound_error_1():  # non-existent data file
    with pytest.raises(FileNotFoundError):
        bnlearn_learn('pc.stable', 'nonexistent.txt')


def test_bnlearn_pc_value_error_1():  # DataFrame has too few columns
    bn = BN.read(TESTDATA_DIR + '/discrete/tiny/ab.dsc')
    data = bn.generate_cases(10)
    with pytest.raises(ValueError):
        bnlearn_learn('pc.stable', data)


def test_bnlearn_pc_value_error_2():  # Data file has too few columns
    with pytest.raises(ValueError):
        bnlearn_learn('pc.stable', TESTDATA_DIR + '/discrete/tiny/ab.dsc')


def test_bnlearn_pc_ab_cb_1k_ok_1():
    bn = BN.read(TESTDATA_DIR + '/discrete/tiny/ab_cb.dsc')
    data = bn.generate_cases(1000)
    pdag, _ = bnlearn_learn('pc.stable', data)
    print('\nPDAG learnt by pc.stable from 1K rows of ab_cb:\n{}'.format(pdag))
    sgs_skeleton(data)
    assert pdag == ex_pdag.ab_cb()


def test_bnlearn_pc_ab_cb_1k_ok_2():
    bn = BN.read(TESTDATA_DIR + '/discrete/tiny/ab_cb.dsc')
    data = bn.generate_cases(1000)
    pdag, _ = bnlearn_learn('pc.stable', data, params={'iss': 10})
    print('\nPDAG learnt by pc.stable from 1K rows of ab_cb:\n{}'.format(pdag))
    assert pdag == ex_pdag.ab_cb()


def test_bnlearn_pc_abc_1k_ok():
    bn = BN.read(TESTDATA_DIR + '/discrete/tiny/abc.dsc')
    data = bn.generate_cases(1000)
    pdag, _ = bnlearn_learn('pc.stable', data)
    print('\nPDAG learnt by pc.stable from 1K rows of abc:\n{}'.format(pdag))
    sgs_skeleton(data)
    assert pdag == ex_pdag.abc4()


def test_bnlearn_pc_abc_dual_1k_ok():
    bn = BN.read(TESTDATA_DIR + '/discrete/tiny/abc_dual.dsc')
    data = bn.generate_cases(1000)
    pdag, _ = bnlearn_learn('pc.stable', data)
    print('\nPDAG learnt by pc.stable from 1K rows of abc_dual:\n{}'
          .format(pdag))
    assert pdag == ex_pdag.abc_acyclic4()


def test_bnlearn_pc_and4_10_1k_ok():  # 1->2->4, 3->2, 1K rows
    bn = BN.read(TESTDATA_DIR + '/discrete/tiny/and4_10.dsc')
    data = bn.generate_cases(1000)
    pdag, _ = bnlearn_learn('pc.stable', data)
    print('\nPDAG learnt by pc.stable from 1K rows of and4_10:\n{}'
          .format(pdag))
    assert pdag == ex_pdag.and4_11()  # NB PC does not learn correct PDAG


def test_bnlearn_pc_cancer_1k_ok_1():  # Cancer, 1K rows
    bn = BN.read(TESTDATA_DIR + '/discrete/small/cancer.dsc')
    data = bn.generate_cases(1000)
    pdag, _ = bnlearn_learn('pc.stable', data)
    print('\nPDAG learnt by pc.stable from 1K rows of Cancer:\n{}'
          .format(pdag))
    assert pdag.edges == {('Dyspnoea', 'Cancer'): EdgeType.DIRECTED,
                          ('Smoker', 'Cancer'): EdgeType.DIRECTED,
                          ('Xray', 'Cancer'): EdgeType.DIRECTED}


def test_bnlearn_pc_cancer_1k_ok_2():  # Cancer, 1K rows, alpha = 0.001
    bn = BN.read(TESTDATA_DIR + '/discrete/small/cancer.dsc')
    data = bn.generate_cases(1000)
    pdag, _ = bnlearn_learn('pc.stable', data, params={'alpha': 0.001})
    print('\nPDAG learnt by pc.stable, 1K rows of Cancer (alpha=0.001):\n{}'
          .format(pdag))
    assert pdag.edges == {('Smoker', 'Cancer'): EdgeType.DIRECTED,
                          ('Xray', 'Cancer'): EdgeType.DIRECTED}


def test_bnlearn_pc_asia_1k_ok_1():  # Asia, 1K rows
    bn = BN.read(TESTDATA_DIR + '/discrete/small/asia.dsc')
    data = bn.generate_cases(1000)
    pdag, _ = bnlearn_learn('pc.stable', data)
    print('\nPDAG learnt by pc.stable from 1K rows of Asia:\n{}'
          .format(pdag))
    assert pdag.edges == {('bronc', 'smoke'): EdgeType.DIRECTED,
                          ('bronc', 'dysp'): EdgeType.UNDIRECTED,
                          ('lung', 'smoke'): EdgeType.DIRECTED,
                          ('lung', 'either'): EdgeType.DIRECTED,
                          ('tub', 'either'): EdgeType.DIRECTED}


def test_bnlearn_pc_asia_1k_ok_2():  # Asia, 1K rows, alpha=0.01
    bn = BN.read(TESTDATA_DIR + '/discrete/small/asia.dsc')
    data = bn.generate_cases(1000)
    pdag, _ = bnlearn_learn('pc.stable', data, params={'alpha': 1E-4})
    print('\nPDAG learnt by pc.stable from 1K rows Asia (alpha=1E-4):\n{}'
          .format(pdag))
    assert pdag.edges == {('bronc', 'smoke'): EdgeType.UNDIRECTED,
                          ('bronc', 'dysp'): EdgeType.UNDIRECTED,
                          ('either', 'xray'): EdgeType.UNDIRECTED,
                          ('either', 'lung'): EdgeType.UNDIRECTED}


def test_bnlearn_pc_gauss_1_ok():  # Gaussian example, 100 rows
    _in = TESTDATA_DIR + '/simple/gauss.data.gz'
    data = Pandas.read(_in, dstype='continuous', N=100)
    pdag, trace = bnlearn_learn('pc.stable', data.sample, dstype='continuous',
                                context={'in': _in, 'id': 'gauss'},
                                params={'test': 'mi-g'})
    print('\nPDAG learnt from 100 rows of gauss: {}\n\n{}'.format(pdag, trace))
    edges = {(e[0], t.value[3], e[1]) for e, t in pdag.edges.items()}
    assert edges == \
        {('D', '->', 'C'),
         ('F', '->', 'C'),
         ('F', '-', 'G'),
         ('B', '-', 'D')}


def test_bnlearn_pc_gauss_2_ok():  # Gaussian example, 100 rows, rev ord
    _in = TESTDATA_DIR + '/simple/gauss.data.gz'
    data = Pandas.read(_in, dstype='continuous', N=100)
    data.set_order(tuple(list(data.get_order())[::-1]))
    pdag, trace = bnlearn_learn('pc.stable', data.sample, dstype='continuous',
                                context={'in': _in, 'id': 'gauss'},
                                params={'test': 'mi-g'})
    print('\nPDAG learnt from 100 rows of gauss: {}\n\n{}'.format(pdag, trace))
    edges = {(e[0], t.value[3], e[1]) for e, t in pdag.edges.items()}
    assert edges == \
        {('C', '->', 'F'),
         ('C', '-', 'D'),
         ('G', '->', 'F'),
         ('B', '-', 'D')}


def test_bnlearn_pc_gauss_3_ok():  # Gaussian example, 5K rows
    _in = TESTDATA_DIR + '/simple/gauss.data.gz'
    data = Pandas.read(_in, dstype='continuous')
    pdag, trace = bnlearn_learn('pc.stable', data.sample, dstype='continuous',
                                context={'in': _in, 'id': 'gauss'},
                                params={'test': 'mi-g'})
    print('\nPDAG learnt from 5K rows of gauss: {}\n\n{}'.format(pdag, trace))
    edges = {(e[0], t.value[3], e[1]) for e, t in pdag.edges.items()}
    assert edges == \
        {('B', '-', 'D'),
         ('B', '->', 'C'),
         ('D', '->', 'F'),
         ('E', '->', 'F'),
         ('G', '->', 'F'),
         ('A', '->', 'C'),
         ('A', '->', 'F')}


def test_bnlearn_pc_gauss_4_ok():  # Gaussian example, 5K rows, rev ord
    _in = TESTDATA_DIR + '/simple/gauss.data.gz'
    data = Pandas.read(_in, dstype='continuous')
    data.set_order(tuple(list(data.get_order())[::-1]))
    pdag, trace = bnlearn_learn('pc.stable', data.sample, dstype='continuous',
                                context={'in': _in, 'id': 'gauss'},
                                params={'test': 'mi-g'})
    print('\nPDAG learnt from 5K rows of gauss: {}\n\n{}'.format(pdag, trace))
    edges = {(e[0], t.value[3], e[1]) for e, t in pdag.edges.items()}
    print(edges)
    assert edges == \
        {('B', '-', 'D'),
         ('B', '->', 'C'),
         ('D', '->', 'F'),
         ('E', '->', 'F'),
         ('G', '->', 'F'),
         ('A', '->', 'C'),
         ('A', '->', 'F')}


def test_bnlearn_pc_sachs_c_1_ok():  # Sachs gauss example, 1K rows
    _in = TESTDATA_DIR + '/experiments/datasets/sachs_c.data.gz'
    data = Pandas.read(_in, dstype='continuous')
    pdag, trace = bnlearn_learn('pc.stable', data.sample, dstype='continuous',
                                context={'in': _in, 'id': 'gauss'},
                                params={'test': 'mi-g'})
    print('\nPDAG rom 1K rows of sachs_c: {}\n\n{}'.format(pdag, trace))
    edges = {(e[0], t.value[3], e[1]) for e, t in pdag.edges.items()}
    assert edges == \
        {('PKA', '->', 'P38'),
         ('Mek', '-', 'Raf'),
         ('Jnk', '-', 'PKC'),
         ('Akt', '-', 'Erk'),
         ('PKA', '->', 'PIP3'),
         ('PIP2', '-', 'Plcg'),
         ('Erk', '->', 'PKA'),
         ('PKC', '->', 'P38'),
         ('Plcg', '->', 'PIP3'),
         ('Mek', '->', 'PKA'),
         ('PIP2', '->', 'PIP3')}


def test_bnlearn_pc_sachs_c_2_ok():  # Sachs gauss example, rev, 1K rows
    _in = TESTDATA_DIR + '/experiments/datasets/sachs_c.data.gz'
    data = Pandas.read(_in, dstype='continuous')
    data.set_order(tuple(list(data.get_order())[::-1]))
    pdag, trace = bnlearn_learn('pc.stable', data.sample, dstype='continuous',
                                context={'in': _in, 'id': 'gauss'},
                                params={'test': 'mi-g'})
    print('\nPDAG rom 1K rows of sachs_c: {}\n\n{}'.format(pdag, trace))
    edges = {(e[0], t.value[3], e[1]) for e, t in pdag.edges.items()}
    assert edges == \
        {('PKA', '->', 'P38'),
         ('Mek', '-', 'Raf'),
         ('Jnk', '-', 'PKC'),
         ('Akt', '-', 'Erk'),
         ('PKA', '->', 'PIP3'),
         ('PIP2', '-', 'Plcg'),
         ('Erk', '->', 'PKA'),
         ('PKC', '->', 'P38'),
         ('Plcg', '->', 'PIP3'),
         ('Mek', '->', 'PKA'),
         ('PIP2', '->', 'PIP3')}