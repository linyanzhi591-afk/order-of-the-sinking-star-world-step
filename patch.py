"""世界暂停与单步补丁：完整文件校验、最外层叠加、精确恢复。"""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
GAME = Path(r'D:\Program Files (x86)\Steam\steamapps\common\Order of the Sinking Star')
MARKER = b'WORLDSTEP_V3\0'
LEGACY_MARKER = b'WORLDSTEP_V1\0'
REPEAT_MARKER = b'WORLDSTEP_V2\0'
LEGACY_PAYLOAD_SHA = '9be7e35f37c0c8263544d3b9ed95e72fa55396dfb98533aa0de9b7770fe763e5'
PAYLOAD_SHA = '03779d5ce7bb8cc71590878f2c868204a15f87b626932be158a478e5c453ce28'
BASE_HASHES = {
    '0ae10a513dae25286fe93d0db4fa8a2df9a473bc07e1734e12bc1ad30166db1c': '原版 Build 26006400',
    'bda4419d1f7e7a79f9aaa3e069ae32fe3e19a827afd8bfb3e21cbab534c60505': '奔跑切换',
    '87ea04ab2be54238cf0fdf6617828a0fcbeb26045228c4ec68aaf4bd62d7f43b': '奔跑＋俯视 v0.1.6＋高亮 P＋网格 v0.2.0 O',
    '4d09b567e98574e195ab1e8a0b5c625678d8cb4476499526bf99ac61cbd83c81': '奔跑＋俯视 v0.1.7＋高亮 P＋静态网格 GRIDSTATIC_V3 O',
    '0d412308f7e7ab27362023517f648138aef3703bb7b764c72a1e2da8a08cbb73': '奔跑＋俯视 v0.1.9＋高亮 P；兼容独立粒子减量资源',
}
HOOKS = {0x262462: ('world_delta_hook', bytes.fromhex('f30f1105ae1b5a00')),
         0x263ffc: ('world_gate_hook', bytes.fromhex('0f837b020000'))}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def payload(rva, legacy=False):
    name, expected = ('payload_v0.1.2.json', '5dea259014d7116c29850637cee03ae8688fa98e268ae63dfbb2d6daea1cf05c') if legacy == 2 else (
        ('payload_v0.1.1.json', LEGACY_PAYLOAD_SHA) if legacy else ('payload.json', PAYLOAD_SHA))
    raw = (ROOT/name).read_bytes()
    if sha(raw) != expected:
        raise ValueError('载荷校验失败，拒绝修改')
    try:
        return json.loads(raw)[str(rva)]
    except KeyError:
        raise ValueError('该补丁组合的映像布局尚未验证') from None

def keycode(name):
    if not isinstance(name, str):
        raise ValueError('按键必须填写名称字符串')
    name = name.upper()
    if len(name) == 1 and (name.isascii() and name.isalnum()):
        return ord(name)
    if name.startswith('F') and name[1:].isdigit() and 1 <= int(name[1:]) <= 12:
        return 111+int(name[1:])
    raise ValueError('按键支持 A-Z、0-9、F1-F12')

def settings():
    config = json.loads((ROOT/'config.json').read_text(encoding='utf8'))
    keys = keycode(config['pause_key']), keycode(config['step_key'])
    validate_keys(keys)
    return keys

def validate_keys(keys):
    if not isinstance(keys, (list, tuple)) or len(keys) != 2:
        raise ValueError('必须提供两个独立按键')
    if any(type(k) is not int or not (48 <= k <= 57 or 65 <= k <= 90 or 112 <= k <= 123) for k in keys):
        raise ValueError('无效虚拟键码')
    if keys[0] == keys[1] or any(k in (79, 80, 81) for k in keys):
        raise ValueError('按键不得相同，也不能占用现有 mod 的 O、P、Q')

def apply(base, keys, legacy=False):
    validate_keys(keys)
    if sha(base) not in BASE_HASHES:
        raise ValueError('游戏版本或其他 mod 已变化，拒绝覆盖；需重新核对兼容性')
    pe = struct.unpack_from('<I', base, 60)[0]
    count = struct.unpack_from('<H', base, pe+6)[0]
    table = pe+24+struct.unpack_from('<H', base, pe+20)[0]
    headers = struct.unpack_from('<I', base, pe+24+60)[0]
    image_end = struct.unpack_from('<I', base, pe+24+56)[0]
    if table+(count+1)*40 > headers or any(base[table+count*40:table+(count+1)*40]):
        raise ValueError('PE 节表空间不足，拒绝覆盖其他 mod')
    p = payload(image_end, legacy)
    result = bytearray(base)
    for rva, (symbol, original) in HOOKS.items():
        off = rva-0xc00
        if base[off:off+len(original)] != original:
            raise ValueError(f'时间钩子已被其他补丁占用：{rva:#x}')
        result[off:off+len(original)] = (b'\xe9'+struct.pack('<i', p['symbols'][symbol]-rva-5)).ljust(len(original), b'\x90')
    # 当前四 mod 组合只剩一个节表项；代码和独立状态放进同一新增节。
    blob = bytearray(base64.b64decode(p['data']))
    struct.pack_into('<II', blob, p['symbols']['world_settings']-image_end, *keys)
    offset = (len(result)+511)&~511
    result.extend(b'\0'*(offset-len(result)))
    result.extend(blob)
    struct.pack_into('<8sIIIIIIHHI', result, table+count*40,
                     b'.wstep', len(blob), image_end, len(blob), offset, 0, 0, 0, 0, 0xe0000060)
    struct.pack_into('<H', result, pe+6, count+1)
    struct.pack_into('<I', result, pe+24+56, image_end+0x3000)
    meta = json.dumps(dict(length=len(base), header=base[:headers].hex(), keys=list(keys),
                           base_sha=sha(base)), separators=(',', ':')).encode()
    marker = REPEAT_MARKER if legacy == 2 else (LEGACY_MARKER if legacy else MARKER)
    result.extend(meta+struct.pack('<I', len(meta))+marker)
    return bytes(result)

def split(data):
    legacy = 2 if data.endswith(REPEAT_MARKER) else (1 if data.endswith(LEGACY_MARKER) else 0)
    marker = REPEAT_MARKER if legacy == 2 else (LEGACY_MARKER if legacy else MARKER)
    if not data.endswith(marker):
        if sha(data) not in BASE_HASHES:
            raise ValueError('主程序包含未验证的版本或修改，拒绝操作')
        return data, None
    try:
        size = struct.unpack_from('<I', data, len(data)-len(marker)-4)[0]
        if not 1 <= size <= 12000:
            raise ValueError('补丁元数据长度异常')
        meta = json.loads(data[-len(marker)-4-size:-len(marker)-4])
        if type(meta['length']) is not int or not 0 < meta['length'] < len(data):
            raise ValueError('基础文件长度异常')
        base = bytearray(data[:meta['length']])
        header = bytes.fromhex(meta['header'])
        if len(header) != 0x400:
            raise ValueError('PE 头长度异常')
        base[:len(header)] = header
        for rva, (_, original) in HOOKS.items():
            base[rva-0xc00:rva-0xc00+len(original)] = original
        base = bytes(base)
        if sha(base) != meta['base_sha'] or apply(base, meta['keys'], legacy=legacy) != data:
            raise ValueError('补丁存在未知修改，拒绝覆盖')
        return base, tuple(meta['keys'])
    except (KeyError, TypeError, IndexError, struct.error, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('世界单步补丁损坏，拒绝操作') from error

def game_running():
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq sinking_star.exe', '/FO', 'CSV', '/NH'],
                            capture_output=True, check=True)
    # 输出可能使用本机 OEM 编码，进程名仍是 ASCII。
    return any(row and row[0].lower() == 'sinking_star.exe' for row in
               csv.reader(io.StringIO(result.stdout.decode('ascii', errors='replace'))))

def replace_game(target, before, after):
    if game_running():
        raise ValueError('游戏正在运行，请关闭游戏后安装或卸载')
    backup = ROOT/'backups'/f'{sha(before)}.exe'
    backup.parent.mkdir(exist_ok=True)
    if backup.exists():
        if backup.read_bytes() != before:
            raise ValueError('已有备份校验失败，拒绝覆盖')
    else:
        with backup.open('xb') as stream:
            stream.write(before)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='world-step-', suffix='.tmp', delete=False) as stream:
            temp = Path(stream.name)
            stream.write(after)
            stream.flush()
            os.fsync(stream.fileno())
        if temp.read_bytes() != after or target.read_bytes() != before or game_running():
            raise ValueError('写入前文件或进程状态变化，已中止')
        os.replace(temp, target)
        temp = None
        if target.read_bytes() != after:
            raise ValueError(f'写入后校验失败；安装前完整备份位于 {backup}')
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return backup

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'install', 'restore'))
    parser.add_argument('--game-dir', type=Path, default=GAME)
    args = parser.parse_args()
    target = args.game_dir/'sinking_star.exe'
    data = target.read_bytes()
    base, installed = split(data)
    if args.action == 'status':
        print(json.dumps(dict(installed=installed is not None, keys=installed,
                              base=BASE_HASHES[sha(base)], sha256=sha(data)), ensure_ascii=False))
        return
    if game_running():
        raise ValueError('游戏正在运行，请关闭游戏后安装或卸载')
    keys = settings() if args.action == 'install' else None
    after = apply(base, keys) if args.action == 'install' else base
    if after == data:
        print('当前已是所需状态，无需修改。')
        return
    # 安装前完成可逆性验证；不修改存档、材质、配置或其他 mod 文件。
    if args.action == 'install':
        assert split(after) == (base, keys)
    backup = replace_game(target, data, after)
    print(f'完成：{args.action}；SHA-256 {sha(after)}；安装前备份：{backup}')

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
