import contextlib
import copy
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from character_anchor_baseline import BASELINE_LOCAL_ROTATIONS
from character_anchor_check import (
    ANCHORS, check_skeleton_data, check_uploaded_character_skeletons, rotation_difference,
)


def baseline():
    return {'Skeleton': {'nodes': [dict(name=name, index=i, parentIndex=-1,
        rotation=copy.deepcopy(BASELINE_LOCAL_ROTATIONS[name])) for i, name in enumerate(ANCHORS)]}}


def rotated(rotation, axis, degrees):
    """右乘一个独立轴旋转，不依赖被测代码计算角度。"""
    a = [rotation[k] for k in 'xyzw']
    b = [0, 0, 0, math.cos(math.radians(degrees) / 2)]
    b['XYZ'.index(axis)] = math.sin(math.radians(degrees) / 2)
    x, y, z, w = a
    u, v, t, s = b
    return dict(zip('xyzw', (w*u+x*s+y*t-z*v, w*v-x*t+y*s+z*u,
                            w*t+x*v-y*u+z*s, w*s-x*u-y*v-z*t)))


class AnchorRulesTest(unittest.TestCase):
    def test_baseline_and_quaternion_sign_and_normalization(self):
        data = baseline()
        self.assertEqual([], check_skeleton_data(data))
        for node in data['Skeleton']['nodes']:
            node['rotation'] = {k: -v*2 for k, v in node['rotation'].items()}
        self.assertEqual([], check_skeleton_data(data))

    def test_xyz_boundary_for_every_anchor(self):
        for name in ANCHORS:
            for axis in 'XYZ':
                for degrees, fail in [(0.0999, False), (0.1, False), (0.1001, True), (90, True)]:
                    with self.subTest(anchor=name, axis=axis, degrees=degrees):
                        data = baseline()
                        node = next(n for n in data['Skeleton']['nodes'] if n['name'] == name)
                        node['rotation'] = rotated(node['rotation'], axis, degrees)
                        issues = check_skeleton_data(data)
                        self.assertEqual(fail, bool(issues))
                        if fail:
                            self.assertEqual('character_anchor_rotation', issues[0]['type'])
                            self.assertAlmostEqual(degrees, issues[0]['angle_degrees'], places=7)

    def test_missing_and_duplicate_each_anchor(self):
        for name in ANCHORS:
            for duplicate in (False, True):
                with self.subTest(anchor=name, duplicate=duplicate):
                    data = baseline()
                    node = next(n for n in data['Skeleton']['nodes'] if n['name'] == name)
                    if duplicate:
                        duplicate_node = copy.deepcopy(node)
                        duplicate_node['index'] = 1000
                        data['Skeleton']['nodes'].append(duplicate_node)
                    else:
                        data['Skeleton']['nodes'].remove(node)
                    issues = check_skeleton_data(data)
                    self.assertEqual(1, len(issues))
                    self.assertEqual('character_anchor_count', issues[0]['type'])
                    self.assertEqual(name, issues[0]['anchor'])

    def test_invalid_rotation_fails_closed(self):
        for rotation in [None, {}, dict(x=0, y=0, z=0, w=0),
                         dict(x=float('nan'), y=0, z=0, w=1)]:
            data = baseline()
            data['Skeleton']['nodes'][0]['rotation'] = rotation
            self.assertEqual('character_anchor_invalid', check_skeleton_data(data)[0]['type'])

    def test_position_scale_order_and_indices_do_not_add_rules(self):
        data = baseline()
        for node in data['Skeleton']['nodes']:
            node.update(index=node['index']+100, position=dict(x=100, y=100, z=100),
                        scale=dict(x=2, y=2, z=2))
        data['Skeleton']['nodes'].reverse()
        self.assertEqual([], check_skeleton_data(data))

    def test_parent_rotation_never_changes_result(self):
        for degrees in (0, 10, 30, 90, 180):
            data = baseline()
            for node in data['Skeleton']['nodes']:
                node['parentIndex'] = 1000
            half = math.radians(degrees)/2
            data['Skeleton']['nodes'].append(dict(name='Root', index=1000, parentIndex=-1,
                rotation=dict(x=0, y=math.sin(half), z=0, w=math.cos(half))))
            with self.subTest(parent_degrees=degrees):
                self.assertEqual([], check_skeleton_data(data))

    def test_parent_compensation_does_not_hide_changed_anchor(self):
        data = baseline()
        node = data['Skeleton']['nodes'][0]
        x, y, z, w = (node['rotation'][k] for k in 'xyzw')
        node['rotation'] = dict(x=y, y=-x, z=-w, w=z)
        node['parentIndex'] = 1000
        data['Skeleton']['nodes'].append(dict(name='Root', index=1000, parentIndex=-1,
            rotation=dict(x=0, y=0, z=1, w=0)))
        issues = check_skeleton_data(data)
        self.assertEqual(['106'], [i['anchor'] for i in issues])
        self.assertAlmostEqual(180, issues[0]['angle_degrees'], places=7)

    def test_parent_and_node_indices_are_not_needed(self):
        data = baseline()
        for node in data['Skeleton']['nodes']:
            del node['parentIndex']
            del node['index']
        self.assertEqual([], check_skeleton_data(data))

    def test_unrelated_parent_fields_do_not_add_rules(self):
        for kind in ('missing', 'cycle', 'duplicate_index', 'invalid_ancestor_rotation'):
            data = baseline()
            node = data['Skeleton']['nodes'][0]
            if kind == 'missing':
                node['parentIndex'] = 999
            elif kind == 'cycle':
                node['parentIndex'] = node['index']
            elif kind == 'duplicate_index':
                data['Skeleton']['nodes'][1]['index'] = node['index']
            else:
                node['parentIndex'] = 999
                data['Skeleton']['nodes'].append(dict(name='root', index=999, parentIndex=-1,
                    rotation=dict(x=0, y=0, z=0, w=0)))
            with self.subTest(kind=kind):
                self.assertEqual([], check_skeleton_data(data))

    def test_actual_problem_commit(self):
        fixture = json.loads((Path(__file__).parent/'fixtures/140616_c84d00e62e12.json').read_text(encoding='utf-8'))
        before = {i['anchor']: i for i in check_skeleton_data(fixture['before'])}
        after = {i['anchor']: i for i in check_skeleton_data(fixture['after'])}
        # 严格基准下提交前也不合格，不能伪造一个通过的历史版本。
        self.assertGreater(before['105']['angle_degrees'], 0.1)
        self.assertGreater(before['106']['angle_degrees'], 0.1)
        self.assertAlmostEqual(89.749635, after['106']['angle_degrees'], places=5)
        self.assertAlmostEqual(90.000140, after['105']['angle_degrees'], places=5)
        a = {n['name']: n for n in fixture['before']['Skeleton']['nodes']}
        b = {n['name']: n for n in fixture['after']['Skeleton']['nodes']}
        self.assertAlmostEqual(89.9905, rotation_difference(a['106']['rotation'], b['106']['rotation'])[0], places=4)
        self.assertAlmostEqual(89.6308, rotation_difference(a['105']['rotation'], b['105']['rotation'])[0], places=4)


class UploadGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.role = self.root/'Assets/remotes/entity/140999'
        self.skeleton = self.role/'Model/renamed.skeleton'
        self.skeleton.parent.mkdir(parents=True)
        self.skeleton.write_text(json.dumps(baseline()), encoding='utf-8')

    def write_invalid(self):
        data = baseline()
        data['Skeleton']['nodes'][0]['rotation'] = dict(x=0, y=0, z=0, w=1)
        self.skeleton.write_text(json.dumps(data), encoding='utf-8')

    def test_direct_skeleton_meta_folder_and_noncharacter_scope(self):
        self.assertEqual([], check_uploaded_character_skeletons([self.skeleton]))
        self.write_invalid()
        for selection in ([self.skeleton], [str(self.skeleton)+'.meta'], [self.role],
                          [self.skeleton, self.skeleton]):
            with self.subTest(selection=selection):
                self.assertEqual(1, len(check_uploaded_character_skeletons(selection)))
        other = self.root/'Assets/remotes/entity/150999/model.skeleton'
        self.assertEqual([], check_uploaded_character_skeletons([other]))

    def test_prefab_resolves_actual_rig_not_filename(self):
        meta = Path(str(self.skeleton)+'.meta')
        meta.write_text(json.dumps({'m_MetaHeader': {'m_GUID': 'test-rig'}}), encoding='utf-8')
        prefab = self.role/'body.prefab'
        prefab.write_text(json.dumps({'m_Object_1': {'SkinnedSkeleton': {'m_Rig': {'m_GUID': 'test-rig'}}}}), encoding='utf-8')
        self.write_invalid()
        self.assertEqual('character_anchor_rotation', check_uploaded_character_skeletons([prefab])[0]['type'])
        self.skeleton.unlink()
        self.assertEqual('character_anchor_invalid', check_uploaded_character_skeletons([prefab])[0]['type'])

    def test_timeline_files_meta_and_folder_are_excluded_case_insensitively(self):
        for folder in ('Timeline', 'TimeLine', 'timeline', 'TIMELINE'):
            directory = self.role/folder/'building/Model'
            directory.mkdir(parents=True, exist_ok=True)
            skeleton = directory/'bad.skeleton'
            skeleton.write_text('{"Skeleton": {"nodes": []}}', encoding='utf-8')
            prefab = directory/'bad.prefab'
            prefab.write_text('broken JSON', encoding='utf-8')
            for selected in (skeleton, str(skeleton)+'.meta', prefab, str(prefab)+'.meta',
                             directory, self.role):
                with self.subTest(folder=folder, selected=selected):
                    self.assertEqual([], check_uploaded_character_skeletons([selected]))
        # 普通主角色仍应阻止上传。
        self.write_invalid()
        issues = check_uploaded_character_skeletons([self.role])
        self.assertEqual(1, len(issues))
        self.assertEqual(str(self.skeleton), issues[0]['file'])

    def test_timeline_substring_is_not_excluded(self):
        directory = self.role/'Timeline_backup'
        directory.mkdir()
        skeleton = directory/'bad.skeleton'
        skeleton.write_text('{"Skeleton": {"nodes": []}}', encoding='utf-8')
        self.assertEqual(6, len(check_uploaded_character_skeletons([skeleton])))

    def test_prefab_reference_to_timeline_rig_is_excluded(self):
        directory = self.role/'Timeline/Model'
        directory.mkdir(parents=True)
        skeleton = directory/'scene.skeleton'
        skeleton.write_text('broken JSON', encoding='utf-8')
        Path(str(skeleton)+'.meta').write_text(json.dumps({'m_MetaHeader': {'m_GUID': 'timeline-rig'}}), encoding='utf-8')
        prefab = self.role/'scene.prefab'
        prefab.write_text(json.dumps({'m_Object_1': {'SkinnedSkeleton': {'m_Rig': {'m_GUID': 'timeline-rig'}}}}), encoding='utf-8')
        self.assertEqual([], check_uploaded_character_skeletons([prefab]))

    def test_timeline_duplicate_guid_does_not_hide_or_ambiguate_main_rig(self):
        guid = 'same-rig'
        Path(str(self.skeleton)+'.meta').write_text(json.dumps({'m_MetaHeader': {'m_GUID': guid}}), encoding='utf-8')
        directory = self.role/'TimeLine/Model'
        directory.mkdir(parents=True)
        copy = directory/'copy.skeleton'
        copy.write_text('broken JSON', encoding='utf-8')
        Path(str(copy)+'.meta').write_text(json.dumps({'m_MetaHeader': {'m_GUID': guid}}), encoding='utf-8')
        prefab = self.role/'body.prefab'
        prefab.write_text(json.dumps({'m_Object_1': {'SkinnedSkeleton': {'m_Rig': {'m_GUID': guid}}}}), encoding='utf-8')
        self.assertEqual([], check_uploaded_character_skeletons([prefab]))
        self.write_invalid()
        issues = check_uploaded_character_skeletons([prefab])
        self.assertEqual(1, len(issues))
        self.assertEqual('character_anchor_rotation', issues[0]['type'])

    def test_unreadable_or_malformed_skeleton_stops(self):
        for value in ('broken json', '[]', '{"Skeleton": {"nodes": null}}'):
            self.skeleton.write_text(value, encoding='utf-8')
            self.assertEqual('character_anchor_invalid', check_uploaded_character_skeletons([self.skeleton])[0]['type'])
        self.skeleton.unlink()
        self.assertEqual('character_anchor_invalid', check_uploaded_character_skeletons([self.skeleton])[0]['type'])

    def test_real_checker_fails_before_git_and_report_is_critical(self):
        with contextlib.redirect_stdout(io.StringIO()):
            from art_resource_manager import ResourceChecker
        self.write_invalid()
        manager = Mock()
        checker = ResourceChecker([str(self.skeleton)], manager, 'CommonResource')
        completed, reports = [], []
        checker.check_completed.connect(lambda ok, message: completed.append((ok, message)))
        checker.detailed_report.connect(reports.append)
        checker.run()
        self.assertFalse(completed[0][0])
        manager.reset_and_pull_repository.assert_not_called()
        self.assertTrue(reports[0]['has_errors'])
        self.assertEqual(1, reports[0]['critical_issues'])
        self.assertIn('自身旋转', reports[0]['report_text'])
        self.assertIn('XYZ', reports[0]['report_text'])

    def test_real_push_rechecks_changed_file_before_any_mutation(self):
        with contextlib.redirect_stdout(io.StringIO()):
            from art_resource_manager import GitSvnManager
        self.assertEqual([], check_uploaded_character_skeletons([self.skeleton]))
        self.write_invalid()  # 模拟检查通过后又修改骨架。
        target = self.root/'CommonResource'
        target.mkdir()
        manager = GitSvnManager.__new__(GitSvnManager)
        manager.git_path, manager.svn_path = str(target), str(self.root)
        with patch('art_resource_manager.subprocess.run') as git, \
             patch('art_resource_manager.shutil.copy2') as copy_file, \
             patch.object(manager, '_execute_safe_deletions') as delete, \
             contextlib.redirect_stdout(io.StringIO()):
            ok, message = manager.push_files_to_git([str(self.skeleton)], folder_upload_modes={'role': {'mode': 'replace'}})
        self.assertFalse(ok)
        self.assertIn('停止上传', message)
        git.assert_not_called()
        copy_file.assert_not_called()
        delete.assert_not_called()
        self.assertEqual([], list(target.iterdir()))

    def test_readonly_cli_writes_versioned_report(self):
        with contextlib.redirect_stdout(io.StringIO()):
            from art_resource_manager import APP_VERSION, run_anchor_check_cli
        report = self.root/'cli-report.json'
        arguments = ['--report', str(report), str(self.skeleton)]
        self.assertEqual(0, run_anchor_check_cli(arguments))
        result = json.loads(report.read_text(encoding='utf-8'))
        self.assertTrue(result['passed'])
        self.assertEqual(APP_VERSION, result['version'])
        self.assertEqual('node', result['rotation_space'])
        self.write_invalid()
        self.assertEqual(1, run_anchor_check_cli(arguments))
        self.assertFalse(json.loads(report.read_text(encoding='utf-8'))['passed'])

    def test_old_version_json_does_not_override_running_program(self):
        from hot_update_manager import HotUpdateManager
        (self.root/'version.json').write_text('{"version": "1.0.23"}', encoding='utf-8')
        updater = HotUpdateManager.__new__(HotUpdateManager)
        updater.current_version, updater.app_path = '1.0.32', str(self.root)
        self.assertEqual('1.0.32', updater.get_current_version())


if __name__ == '__main__':
    unittest.main()
