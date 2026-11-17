"""只读检查 140 系列角色挂点在骨架空间中的绝对旋转，以 140620 为准。"""

import json
import math
import re
from pathlib import Path

from character_anchor_baseline import BASELINE_ABSOLUTE_ROTATIONS


ANCHORS = ('106', '105', '101', '102', '103', '109')
MAX_ANGLE_DEGREES = 0.1
ISSUE_TYPES = {'character_anchor_count', 'character_anchor_rotation', 'character_anchor_invalid'}


def _quaternion(rotation):
    values = tuple(float(rotation[k]) for k in 'xyzw')
    if not all(math.isfinite(v) for v in values):
        raise ValueError('旋转包含非有限数值')
    norm = math.sqrt(sum(v * v for v in values))
    if not math.isfinite(norm) or norm < 1e-12:
        raise ValueError('旋转四元数无效')
    return tuple(v / norm for v in values)


def rotation_difference(reference, current):
    """返回最短旋转角，以及 XYZ 三条轴的方向偏差；q 和 -q 等价。"""
    a, b = _quaternion(reference), _quaternion(current)
    # atan2 比 acos(dot) 在 0.1 度附近更稳定。
    if sum(x * y for x, y in zip(a, b)) < 0:
        b = tuple(-v for v in b)
    difference = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
    total = math.sqrt(sum((x + y) ** 2 for x, y in zip(a, b)))
    angle = math.degrees(4 * math.atan2(difference, total))

    def axes(q):
        x, y, z, w = q
        return ((1-2*(y*y+z*z), 2*(x*y+z*w), 2*(x*z-y*w)),
                (2*(x*y-z*w), 1-2*(x*x+z*z), 2*(y*z+x*w)),
                (2*(x*z+y*w), 2*(y*z-x*w), 1-2*(x*x+y*y)))

    axis_angles = {}
    for axis, va, vb in zip('XYZ', axes(a), axes(b)):
        chord = math.sqrt(sum((x-y)**2 for x, y in zip(va, vb)))
        axis_angles[axis] = math.degrees(2 * math.asin(min(1.0, chord / 2)))
    return angle, axis_angles


def _issue(kind, path, message, **details):
    return dict(type=kind, file=str(path), message=message, **details)


def absolute_rotation(node, nodes_by_index):
    """沿 parentIndex 累乘到根，包含根自身旋转；不加入场景或 Prefab 实例变换。"""
    result = (0.0, 0.0, 0.0, 1.0)
    visited = set()
    while True:
        index = node['index']
        if index in visited:
            raise ValueError(f'骨骼父链存在循环：index={index}')
        visited.add(index)
        x, y, z, w = _quaternion(node['rotation'])
        u, v, t, s = result
        # parent * child（xyzw），从叶子向上累计。
        result = (w*u+x*s+y*t-z*v, w*v-x*t+y*s+z*u,
                  w*t+x*v-y*u+z*s, w*s-x*u-y*v-z*t)
        parent_index = node['parentIndex']
        if type(parent_index) is not int:
            raise ValueError(f'无效 parentIndex：{parent_index}')
        if parent_index == -1:
            return dict(zip('xyzw', _quaternion(dict(zip('xyzw', result)))))
        if parent_index not in nodes_by_index:
            raise ValueError(f'找不到父骨骼 index={parent_index}')
        node = nodes_by_index[parent_index]


def check_skeleton_data(data, path=''):
    """检查唯一性，并将局部 rotation 沿完整父链转换为骨架空间绝对方向。"""
    try:
        nodes = data['Skeleton']['nodes']
        if not isinstance(nodes, list) or not all(isinstance(n, dict) for n in nodes):
            raise ValueError('Skeleton.nodes 格式无效')
        nodes_by_index = {}
        for node in nodes:
            index = node['index']
            if type(index) is not int or index < 0 or index in nodes_by_index:
                raise ValueError(f'骨骼 index 无效或重复：{index}')
            nodes_by_index[index] = node
    except (KeyError, TypeError, ValueError) as exc:
        return [_issue('character_anchor_invalid', path, f'无法检查角色骨骼：{exc}')]
    issues = []
    for name in ANCHORS:
        matches = [n for n in nodes if n.get('name') == name]
        if len(matches) != 1:
            issues.append(_issue('character_anchor_count', path,
                f'挂点 {name} 必须存在且唯一，当前数量：{len(matches)}；停止上传。', anchor=name))
            continue
        try:
            current = absolute_rotation(matches[0], nodes_by_index)
            angle, axes = rotation_difference(BASELINE_ABSOLUTE_ROTATIONS[name], current)
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            issues.append(_issue('character_anchor_invalid', path,
                f'挂点 {name} 旋转数据无效：{exc}；停止上传。', anchor=name))
            continue
        # 仅吸收浮点运算舍入误差，边界 0.1° 允许通过。
        if max(angle, *axes.values()) > MAX_ANGLE_DEGREES + 1e-9:
            issues.append(_issue('character_anchor_rotation', path,
                f'挂点 {name} 在骨架空间的绝对旋转偏离 140620：{angle:.6f}°；'
                f'XYZ 轴方向偏差：{axes["X"]:.6f}° / {axes["Y"]:.6f}° / {axes["Z"]:.6f}°；'
                f'允许 ≤ {MAX_ANGLE_DEGREES}°，停止上传。',
                anchor=name, angle_degrees=angle, axis_degrees=axes,
                absolute_rotation=current, rotation_space='skeleton'))
    return issues


def _role_root(path):
    """兼容 SVN 和映射后的 CommonResource 路径，排除其他类型资源。"""
    for parent in path.parents:
        if re.fullmatch(r'140\d{3}', parent.name) and parent.parent.name.lower() == 'entity':
            return parent
    return None


def check_uploaded_character_skeletons(upload_files):
    """检查上传骨架及角色 prefab 实际引用的骨架；读取失败时禁止放行。"""
    issues, skeletons, prefabs = [], {}, []
    for raw in upload_files:
        path = Path(raw)
        if path.suffix.lower() == '.meta':
            path = path.with_suffix('')
        candidates = path.rglob('*') if path.is_dir() else (path,)
        for candidate in candidates:
            role = _role_root(candidate)
            if role is None:
                continue
            suffix = candidate.suffix.lower()
            if suffix == '.skeleton':
                skeletons[str(candidate.resolve()).casefold()] = candidate
            elif suffix == '.prefab':
                prefabs.append((candidate, role))

    rig_maps = {}
    for prefab, role in dict.fromkeys(prefabs):
        try:
            data = json.loads(prefab.read_text(encoding='utf-8-sig'))
            rigs = []
            for obj in data.values():
                if isinstance(obj, dict) and 'SkinnedSkeleton' in obj:
                    rig = obj['SkinnedSkeleton']['m_Rig']['m_GUID']
                    if rig and set(rig) != {'0'}:
                        rigs.append(rig)
            if not rigs:
                continue
            if role not in rig_maps:
                mapping = {}
                for meta in role.rglob('*.skeleton.meta'):
                    try:
                        guid = json.loads(meta.read_text(encoding='utf-8-sig'))['m_MetaHeader']['m_GUID']
                    except (OSError, ValueError, KeyError, TypeError):
                        continue
                    mapping.setdefault(guid, []).append(meta.with_suffix(''))
                rig_maps[role] = mapping
            for rig in set(rigs):
                matches = rig_maps[role].get(rig, [])
                if len(matches) != 1:
                    raise ValueError(f'无法唯一定位角色骨骼 GUID {rig}（找到 {len(matches)} 个）')
                path = matches[0]
                skeletons[str(path.resolve()).casefold()] = path
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            issues.append(_issue('character_anchor_invalid', prefab,
                f'无法检查角色引用的骨骼：{exc}；停止上传。'))

    for path in sorted(skeletons.values()):
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            issues.extend(check_skeleton_data(data, path))
        except (OSError, ValueError, TypeError) as exc:
            issues.append(_issue('character_anchor_invalid', path,
                f'无法读取角色骨骼：{exc}；停止上传。'))
    return issues
