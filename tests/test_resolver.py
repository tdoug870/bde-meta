# tests.test_resolver

from collections import defaultdict
from os.path     import join as pjoin
from unittest    import TestCase

from bdemeta.resolver import bde_items, PackageResolver, UnitResolver
from bdemeta.types    import Component
from tests.patcher    import OsPatcher

import bdemeta.resolver

class BdeItemsTest(TestCase):
    def setUp(self):
        self._patcher = OsPatcher(bdemeta.resolver, {
            'one': {
                'char': u'a',
                'commented': {
                    'item': u'# a',
                },
                'real': {
                    'one': {
                        'comment': u'a\n#b',
                    },
                },
            },
            'longer': {
                'char': u'ab',
            },
            'two': {
                'same': {
                    'line': u'a b',
                },
                'diff': {
                    'lines': u'a\nb',
                },
                'commented': {
                    'same': {
                        'line': u'# a b',
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_one_char_item(self):
        assert(['a'] == bde_items('one', 'char'))

    def test_longer_char_item(self):
        assert(['ab'] == bde_items('longer', 'char'))

    def test_two_items_on_same_line(self):
        assert(['a', 'b'] == bde_items('two', 'same', 'line'))

    def test_item_on_each_line(self):
        assert(['a', 'b'] == bde_items('two', 'diff', 'lines'))

    def test_one_commented_item(self):
        assert([] == bde_items('one', 'commented', 'item'))

    def test_two_commented_items_same_line(self):
        assert([] == bde_items('two', 'commented', 'same', 'line'))

    def test_one_real_one_comment(self):
        assert(['a'] == bde_items('one', 'real', 'one', 'comment'))

class PackageResolverTest(TestCase):
    def setUp(self):
        self.config = {
            'roots': ['r'],
            'units': defaultdict(lambda: dict((('internal_cflags', []),
                                               ('external_cflags', [])))),
        }
        self.config['units']['g1p1']['external_cflags'] = ['foo']
        self._patcher = OsPatcher(bdemeta.resolver, {
            'r': {
                'g1': {
                    'g1p1': {
                        'package': {
                            'g1p1.dep': u'',
                            'g1p1.mem': u'',
                        },
                    },
                    'g1p2': {
                        'package': {
                            'g1p2.dep': u'',
                            'g1p2.mem': u'g1p2_c1',
                        },
                    },
                    'g1p3': {
                        'package': {
                            'g1p3.dep': u'',
                            'g1p3.mem': u'g1p3_c1',
                        },
                        'g1p3_c1.t.cpp': u'',
                    },
                    'g1+p4': {
                        'package': {
                            'g1+p4.dep': u'',
                            'g1+p4.mem': u'',
                        },
                        'a.cpp': u'',
                        'b.cpp': u'',
                    },
                    'g1+p5': {
                        'package': {
                            'g1+p5.dep': u'',
                            'g1+p5.mem': u'',
                        },
                        'a.c': u'',
                    },
                    'g1+p6': {
                        'package': {
                            'g1+p6.dep': u'',
                            'g1+p6.mem': u'',
                        },
                        'a.x': u'',
                    },
                },
                'g2': {
                    'g2p1': {
                        'package': {
                            'g2p1.dep': u'',
                            'g2p1.mem': u'',
                        },
                    },
                    'g2p2': {
                        'package': {
                            'g2p2.dep': u'g2p1',
                            'g2p2.mem': u'',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_empty_dependencies(self):
        r = PackageResolver(self.config, pjoin('r', 'g1'))
        assert(set() == r.dependencies('g1p1'))

    def test_non_empty_dependencies(self):
        r = PackageResolver(self.config, pjoin('r', 'g2'))
        assert(set(['g2p1']) == r.dependencies('g2p2'))

    def test_empty_package(self):
        r = PackageResolver(self.config, pjoin('r', 'g1'))
        p = r.resolve('g1p1', {})
        assert('g1p1'                              == p)
        assert([]                                  == p.dependencies())
        assert(['foo', pjoin('-Ir', 'g1', 'g1p1')] == p.cflags())
        assert([]                                  == p.ld_input())
        assert([]                                  == p.components())

    def test_one_non_driver_component(self):
        r = PackageResolver(self.config, pjoin('r', 'g1'))
        p = r.resolve('g1p2', {})
        assert('g1p2'                              == p)
        assert([]                                  == p.dependencies())
        assert([pjoin('-Ir', 'g1', 'g1p2')]        == p.cflags())
        assert([]                                  == p.ld_input())
        assert(1                                   == len(p.components()))
        assert(bdemeta.types.Component('g1p2_c1',
                                       pjoin('r', 'g1', 'g1p2', 'g1p2_c1.cpp'),
                                       None) in p.components())

    def test_one_driver_component(self):
        r = PackageResolver(self.config, pjoin('r', 'g1'))
        p = r.resolve('g1p3', {})
        assert('g1p3'                              == p)
        assert([]                                  == p.dependencies())
        assert([pjoin('-Ir', 'g1', 'g1p3')]        == p.cflags())
        assert([]                                  == p.ld_input())
        assert(1                                   == len(p.components()))
        assert(bdemeta.types.Component(
                  'g1p3_c1',
                  pjoin('r', 'g1', 'g1p3', 'g1p3_c1.cpp'),
                  pjoin('r', 'g1', 'g1p3', 'g1p3_c1.t.cpp')) in p.components())

    def test_empty_package_with_dependency(self):
        r = PackageResolver(self.config, pjoin('r', 'g2'))
        p1 = r.resolve('g2p1', {})
        assert('g2p1' == p1)
        assert([]     == p1.dependencies())
        p2 = r.resolve('g2p2', { 'g2p1': p1 })
        assert('g2p2' == p2)
        assert([p1]   == p2.dependencies())

    def test_thirdparty_package_lists_cpps(self):
        r = PackageResolver(self.config, pjoin('r', 'g1'))
        p = r.resolve('g1+p4', {})
        assert('g1+p4'                              == p)
        assert([]                                   == p.dependencies())
        assert([pjoin('-Ir', 'g1', 'g1+p4')]        == p.cflags())
        assert([]                                   == p.ld_input())
        assert(2                                    == len(p.components()))
        assert(bdemeta.types.Component('g1+p4_a',
                                       pjoin('r', 'g1', 'g1+p4', 'a.cpp'),
                                       None) in p.components())
        assert(bdemeta.types.Component('g1+p4_b',
                                       pjoin('r', 'g1', 'g1+p4', 'b.cpp'),
                                       None) in p.components())

    def test_thirdparty_package_lists_cs(self):
        r = PackageResolver(self.config, pjoin('r', 'g1'))
        p = r.resolve('g1+p5', {})
        assert('g1+p5'                              == p)
        assert([]                                   == p.dependencies())
        assert([pjoin('-Ir', 'g1', 'g1+p5')]        == p.cflags())
        assert([]                                   == p.ld_input())
        assert(1                                    == len(p.components()))
        assert(bdemeta.types.Component('g1+p5_a',
                                       pjoin('r', 'g1', 'g1+p5', 'a.c'),
                                       None) in p.components())

    def test_thirdparty_package_ignores_non_c_non_cpp(self):
        r = PackageResolver(self.config, pjoin('r', 'g1'))
        p = r.resolve('g1+p6', {})
        assert('g1+p6'                              == p)
        assert([]                                   == p.dependencies())
        assert([pjoin('-Ir', 'g1', 'g1+p6')]        == p.cflags())
        assert([]                                   == p.ld_input())
        assert(0                                    == len(p.components()))

    def test_level_two_package_has_dependency(self):
        r = PackageResolver(self.config, pjoin('r', 'g2'))

        p1 = r.resolve('g2p1', {})
        assert('g2p1'                              == p1)
        assert([]                                  == p1.dependencies())
        assert([pjoin('-Ir', 'g2', 'g2p1')]        == p1.cflags())
        assert([]                                  == p1.ld_input())
        assert(0                                   == len(p1.components()))

        p2 = r.resolve('g2p2', { 'g2p1': p1 })
        assert('g2p2'                              == p2)
        assert([p1]                                == p2.dependencies())
        assert([pjoin('-Ir', 'g2', 'g2p2')]        == p2.cflags())
        assert([]                                  == p2.ld_input())
        assert(0                                   == len(p2.components()))

class UnitResolverTest(TestCase):
    def setUp(self):
        self.config = {
            'roots': ['r'],
            'units': defaultdict(lambda: dict((('internal_cflags', []),
                                               ('external_cflags', []),
                                               ('ld_args',         []),
                                               ('deps',            [])))),
        }
        self.config['units']['#universal']['external_cflags'] = ['foo']
        self.config['units']['bar']['external_cflags']        = ['baz']
        self.config['units']['bar']['ld_args']                = ['bam']
        self._patcher = OsPatcher(bdemeta.resolver, {
            'r': {
                'applications': {
                    'm_app': {
                        'application': {
                            'm_app.dep': u'gr2',
                        },
                    },
                },
                'groups': {
                    'gr1': {
                        'group': {
                            'gr1.dep': u'',
                            'gr1.mem': u'gr1p1 gr1p2',
                        },
                        'gr1p1': {
                            'package': {
                                'gr1p1.dep': u'',
                            },
                        },
                        'gr1p2': {
                            'package': {
                                'gr1p2.dep': u'',
                            },
                        },
                    },
                    'gr2': {
                        'group': {
                            'gr2.dep': u'gr1',
                        },
                    },
                },
            },
        })

    def tearDown(self):
        self._patcher.reset()

    def test_group_identification(self):
        r = UnitResolver(self.config)
        assert({
            'type': 'group',
            'path': pjoin('r', 'groups', 'gr1')
        } == r.identify('gr1'))

    def test_application_identification(self):
        r = UnitResolver(self.config)
        assert({
            'type': 'application',
            'path': pjoin('r', 'applications', 'm_app')
        } == r.identify('m_app'))

    def test_non_identification(self):
        r = UnitResolver(self.config)
        assert({ 'type': None } == r.identify('foo'))

    def test_universal_unit_no_dependency(self):
        r = UnitResolver(self.config)
        assert(set() == r.dependencies('#universal'))

    def test_non_universal_unit_has_universal_dependency(self):
        r = UnitResolver(self.config)
        assert(set(['#universal']) == r.dependencies('foo'))

    def test_group_has_universal_dependency(self):
        r = UnitResolver(self.config)
        assert(set(['#universal']) == r.dependencies('gr1'))

    def test_group_with_one_dependency(self):
        r = UnitResolver(self.config)
        assert(set(['gr1', '#universal']) == r.dependencies('gr2'))

    def test_application_with_one_dependency(self):
        r = UnitResolver(self.config)
        assert(set(['gr2', '#universal']) == r.dependencies('m_app'))

    def test_universal_unit_resolution(self):
        r = UnitResolver(self.config)
        u = r.resolve('#universal', {})
        assert('#universal' == u)
        assert(['foo']      == u.cflags())

    def test_unknown_target_resolution(self):
        r = UnitResolver(self.config)
        universal = r.resolve('#universal', {})
        bar       = r.resolve('bar',        { '#universal': universal })
        assert('bar'   == bar)
        assert(['baz'] == bar.cflags())
        assert(['bam'] == bar.ld_args())

    def test_level_one_group_resolution(self):
        r = UnitResolver(self.config)

        universal = r.resolve('#universal', {})
        gr1       = r.resolve('gr1',        { '#universal': universal })
        assert('gr1' == gr1)

    def test_level_one_group_resolution_packages(self):
        ur = UnitResolver(self.config)
        pr = PackageResolver(self.config, pjoin('r', 'groups', 'gr1'))

        universal = ur.resolve('#universal', {})
        gr1       = ur.resolve('gr1',        { '#universal': universal })
        assert('gr1' == gr1)
        assert(resolve(pr, ['gr1p1', 'gr1p2']) == gr1._packages)

    def test_level_two_group_resolution(self):
        r = UnitResolver(self.config)

        universal = r.resolve('#universal', {})
        gr1       = r.resolve('gr1',        { '#universal': universal  })
        gr2       = r.resolve('gr2',        { '#universal': universal,
                                              'gr1':        gr1        })
        assert('gr2' == gr2)

    def test_application_resolution(self):
        r = UnitResolver(self.config)

        universal = r.resolve('#universal', {})
        gr1       = r.resolve('gr1',        { '#universal': universal  })
        gr2       = r.resolve('gr2',        { '#universal': universal,
                                              'gr1':        gr1        })
        m_app     = r.resolve('m_app',      { '#universal': universal,
                                              'gr1':        gr1,
                                              'gr2':        gr2        })
        assert('m_app' == m_app)
