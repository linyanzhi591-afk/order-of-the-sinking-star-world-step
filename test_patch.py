"""隔离映像与真实 x64 钩子测试，不写游戏、不操作存档。"""
import base64
import ctypes as C
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch as mock
import patch as mod

ORIGINAL = mod.ROOT.parent/'toggle-run'/'sinking_star.original.exe'
RUN = mod.ROOT.parent/'toggle-run'/'sinking_star.toggle-run.exe'
COMBINED = mod.GAME/'sinking_star.exe'

def jump(source, target):
    return b'\xe9'+struct.pack('<i', target-source-5)

class WorldStepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.bases = [cls.original, RUN.read_bytes()]
        current, _ = mod.split(COMBINED.read_bytes())
        if mod.sha(current) in mod.BASE_HASHES:
            cls.bases.append(current)
        else:
            raise RuntimeError('当前 mod 组合已变化，必须重新核对，不能跳过兼容测试')
        cls.k = C.WinDLL('kernel32', use_last_error=True)
        cls.k.VirtualAlloc.argtypes = [C.c_void_p, C.c_size_t, C.c_uint32, C.c_uint32]
        cls.k.VirtualAlloc.restype = C.c_void_p
        cls.k.VirtualFree.argtypes = [C.c_void_p, C.c_size_t, C.c_uint32]
        cls.k.LoadLibraryExW.argtypes = [C.c_wchar_p, C.c_void_p, C.c_uint32]
        cls.k.LoadLibraryExW.restype = C.c_void_p
        cls.k.FreeLibrary.argtypes = [C.c_void_p]

    def test_01_roundtrip_and_compatibility(self):
        for base in self.bases:
            for keys in ((78, 77), (117, 118)):
                with self.subTest(base=mod.sha(base), keys=keys):
                    result = mod.apply(base, keys)
                    self.assertEqual(mod.split(result), (base, keys))
                    # 现有代码、资源、追加节和旧补丁元数据全部逐字节保留。
                    allowed = set(range(0x400))
                    for rva, (_, before) in mod.HOOKS.items():
                        allowed.update(range(rva-0xc00, rva-0xc00+len(before)))
                    self.assertTrue(all(i in allowed or a == b for i, (a, b) in enumerate(zip(base, result))))
                    with tempfile.TemporaryDirectory(dir=mod.ROOT, prefix='tmp-map-') as directory:
                        exe = Path(directory)/'image.exe'
                        exe.write_bytes(result)
                        mapped = self.k.LoadLibraryExW(str(exe), None, 1)
                        self.assertTrue(mapped, C.get_last_error())
                        self.k.FreeLibrary(mapped)

    def test_02_reject_unknown_and_tampering(self):
        base = self.bases[-1]
        result = mod.apply(base, (78, 77))
        for pos in (0x1200, 0x262462-0xc00, len(base)+600, len(result)-25):
            changed = bytearray(result)
            changed[pos] ^= 1
            with self.subTest(pos=pos), self.assertRaises(ValueError):
                mod.split(bytes(changed))
        changed = bytearray(base)
        changed[0x1200] ^= 1
        with self.assertRaises(ValueError):
            mod.apply(bytes(changed), (78, 77))
        for keys in ((78, 78), (79, 77), (78, 80), (81, 77), (True, 77), (0, 77)):
            with self.subTest(keys=keys), self.assertRaises(ValueError):
                mod.apply(base, keys)

    def test_03_atomic_install_restore_and_running_guard(self):
        base = self.bases[-1]
        result = mod.apply(base, (78, 77))
        with tempfile.TemporaryDirectory(dir=mod.ROOT, prefix='tmp-install-') as directory:
            root = Path(directory)
            (root/'payload.json').write_bytes((mod.ROOT/'payload.json').read_bytes())
            game = root/'game with spaces'
            game.mkdir()
            target = game/'sinking_star.exe'
            target.write_bytes(base)
            with mock.object(mod, 'ROOT', root), mock.object(mod, 'game_running', return_value=True):
                with self.assertRaises(ValueError):
                    mod.replace_game(target, base, result)
                self.assertEqual(target.read_bytes(), base)
                self.assertFalse((root/'backups').exists())
            with mock.object(mod, 'ROOT', root), mock.object(mod, 'game_running', return_value=False):
                backup = mod.replace_game(target, base, result)
                self.assertEqual(backup.read_bytes(), base)
                self.assertEqual(target.read_bytes(), result)
                mod.replace_game(target, result, mod.split(target.read_bytes())[0])
                self.assertEqual(target.read_bytes(), base)
                # 再次安装、改键、卸载精确回到其他四 mod 组合。
                other = mod.apply(base, (117, 118))
                mod.replace_game(target, base, other)
                self.assertEqual(mod.split(target.read_bytes()), (base, (117, 118)))
                mod.replace_game(target, other, base)
                self.assertEqual(target.read_bytes(), base)

    def test_04_real_hooks_and_native_loop(self):
        for image_end in (0x113c000, 0x1146000, 0x1143000):
            with self.subTest(image_end=hex(image_end)):
                self.execute_hooks(image_end)

    def test_05_cmd_paths_and_exit_codes(self):
        with tempfile.TemporaryDirectory(dir=mod.ROOT, prefix='tmp-entry-') as directory:
            root = Path(directory)/'launcher path with spaces'
            root.mkdir()
            for action in ('install', 'restore', 'status'):
                raw = (mod.ROOT/(action+'.cmd')).read_bytes()
                self.assertFalse(raw.startswith(b'\xef\xbb\xbf'))
                self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))
                (root/(action+'.cmd')).write_bytes(raw)
                # 入口仅运行隔离桩，检验含空格路径、参数和失败返回码传播。
                (root/'patch.py').write_text(
                    'import sys\nassert sys.argv[1:] == '+repr([action])+'\nraise SystemExit(17)\n',
                    encoding='utf8')
                result = subprocess.run(['cmd.exe', '/d', '/c', action+'.cmd'], cwd=root,
                                        input=b'\n', capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 17, repr(result.stdout+result.stderr))

    def test_06_legacy_upgrade(self):
        for base in self.bases:
            for legacy, marker in ((1, mod.LEGACY_MARKER), (2, mod.REPEAT_MARKER)):
                old = mod.apply(base, (78, 77), legacy=legacy)
                self.assertTrue(old.endswith(marker))
                self.assertEqual(mod.split(old), (base, (78, 77)))
                new = mod.apply(mod.split(old)[0], (78, 77))
                self.assertTrue(new.endswith(mod.MARKER))
                self.assertEqual(mod.split(new), (base, (78, 77)))
                self.assertNotEqual(new, old)

    def execute_hooks(self, image_end):
        address = self.k.VirtualAlloc(None, 0x1151000, 0x3000, 0x40)
        self.assertTrue(address)
        refs = []
        try:
            p = mod.payload(image_end)
            blob = base64.b64decode(p['data'])
            C.memmove(address+image_end, blob, len(blob))
            state = (C.c_uint32*6).from_address(address+p['symbols']['world_settings'])
            steps = C.c_uint64.from_address(address+p['symbols']['world_settings']+32)
            native_step = C.c_float.from_address(address+0x8022e4)
            native_step.value = 0.033
            delta = C.c_float.from_address(address+0x804018)
            count = C.c_uint64.from_address(address+0x114f000)
            captured = C.c_float.from_address(address+0x114f008)
            context = dict(keys=set(), pid=77)
            fg = C.CFUNCTYPE(C.c_void_p)(lambda: 123)
            def window(hwnd, out):
                C.c_uint32.from_address(out).value = context['pid']
                return 1
            wp = C.CFUNCTYPE(C.c_uint32, C.c_void_p, C.c_void_p)(window)
            def proc(module, name):
                return C.cast(fg if name == b'GetForegroundWindow' else wp, C.c_void_p).value
            callbacks = {
                0x7c0258: C.CFUNCTYPE(C.c_void_p, C.c_void_p)(lambda _: 1),
                0x7c0260: C.CFUNCTYPE(C.c_void_p, C.c_void_p, C.c_char_p)(proc),
                0x7c01f8: C.CFUNCTYPE(C.c_uint32)(lambda: 77),
                0x7c0000: C.CFUNCTYPE(C.c_short, C.c_int)(lambda key: -32768 if key in context['keys'] else 0),
            }
            refs.extend((fg, wp, *callbacks.values()))
            for rva, callback in callbacks.items():
                C.c_void_p.from_address(address+rva).value = C.cast(callback, C.c_void_p).value
            def put(rva, code):
                C.memmove(address+rva, code, len(code))
            # 从真正的 delta 钩子进入，再执行原生时间累加指令。
            wrapper = b'\x48\x83\xec\x28'
            wrapper += jump(0x114e000+len(wrapper), p['symbols']['world_delta_hook'])
            put(0x114e000, wrapper)
            tail = self.original[0x26246a-0xc00:0x26247e-0xc00]+b'\x48\x83\xc4\x28\xc3'
            put(0x26246a, tail)
            filter_delta = C.CFUNCTYPE(None, C.c_float)(address+0x114e000)
            # 执行游戏自己的完整正向子步循环；只有实体更新体替换成计数桩。
            begin, end = 0x263fec, 0x26442f
            put(begin, self.original[begin-0xc00:end-0xc00])
            put(0x263ffc, jump(0x263ffc, p['symbols']['world_gate_hook'])+b'\x90')
            put(0x264002, jump(0x264002, 0x114e400))
            put(0x393570, b'\xc3')
            counter = b'\x48\xff\x05'+struct.pack('<i', 0x114f000-(0x30d200+7))
            counter += b'\xf3\x0f\x11\x0d'+struct.pack('<i', 0x114f008-(0x30d200+len(counter)+8))+b'\xc3'
            put(0x30d200, counter)
            put(0x114e500, b'\xc3')
            C.c_void_p.from_address(address+0x805298).value = address+0x114e500
            obj = C.create_string_buffer(0x8000)
            C.c_void_p.from_address(address+0x805318).value = C.addressof(obj)
            # Windows x64 ABI：保留原生循环使用的全部非易失寄存器。
            save = bytes.fromhex('5355565741544155415641574881ec280a0000')
            restore = b''
            for reg in range(6, 16):
                rex = b'\x44' if reg >= 8 else b''
                offset = struct.pack('<I', 0x980+(reg-6)*16)
                save += rex+b'\x0f\x11'+bytes([0x84+((reg&7)<<3)])+b'\x24'+offset
                restore += rex+b'\x0f\x10'+bytes([0x84+((reg&7)<<3)])+b'\x24'+offset
            save += b'\x48\x89\xce'
            save += jump(0x114e100+len(save), begin)
            restore += bytes.fromhex('4881c4280a0000415f415e415d415c5f5e5d5bc3')
            put(0x114e100, save)
            put(0x114e400, restore)
            native_loop = C.CFUNCTYPE(None, C.c_void_p)(address+0x114e100)
            total = C.c_double.from_address(address+0x804020)
            def frame(keys=(), dt=1/60, pid=77):
                context.update(keys=set(keys), pid=pid)
                previous_count, previous_time = count.value, total.value
                filter_delta(dt)
                out = delta.value
                native_loop(C.addressof(obj))
                self.assertAlmostEqual(total.value-previous_time, out, places=6)
                return out, count.value-previous_count
            # 自然运行保持原生帧时长及拆步数；原版零步长仍调用一次。
            self.assertEqual(frame()[1], 1)
            self.assertEqual(frame(dt=0.1)[1], 4)
            self.assertEqual(frame(dt=0)[1], 1)
            self.assertEqual(frame((78,)), (0, 0))
            frozen_time = total.value
            for _ in range(300):
                self.assertEqual(frame((78,)), (0, 0))
            self.assertEqual(total.value, frozen_time)
            frame()
            # 首次等待99毫秒；第二次起只等待33毫秒，松开后重新等待。
            self.assertEqual(frame((77,))[1], 1)
            self.assertEqual(frame((77,), 0.098), (0, 0))
            self.assertEqual(frame((77,), 0.0011)[1], 1)
            self.assertEqual(frame((77,), 0.032), (0, 0))
            self.assertEqual(frame((77,), 0.0011)[1], 1)
            self.assertEqual(frame(), (0, 0))
            self.assertEqual(frame((77,))[1], 1)
            self.assertEqual(frame((77,), 0.066), (0, 0))
            self.assertEqual(frame(), (0, 0))
            for dt in (1/240, 1/60, 0.15):
                before_steps = steps.value
                out, ticks = frame((77,), dt)
                self.assertEqual(out, native_step.value)
                self.assertEqual(ticks, 1)
                self.assertEqual(captured.value, native_step.value)
                for _ in range(100):
                    out, ticks = frame((77,), dt)
                    self.assertIn(ticks, (0, 1))
                    self.assertEqual(out, native_step.value if ticks else 0)
                expected = 1+min(100, max(0, int(100*C.c_float(dt).value/native_step.value)-2))
                self.assertEqual(steps.value-before_steps, expected)
                for _ in range(10):
                    self.assertEqual(frame(), (0, 0))
            # 短按只推进一刻，松开后立即停住；再次短按可继续。
            old_steps = steps.value
            self.assertEqual(frame((77,))[1], 1)
            for _ in range(10):self.assertEqual(frame(), (0, 0))
            self.assertEqual(steps.value, old_steps+1)
            # 恢复不会补跑暂停期间积攒的时间。
            out, ticks = frame((78,), 1/60)
            self.assertAlmostEqual(out, 1/60, places=6)
            self.assertEqual(ticks, 1)
            frame()
            # 运行中 M 直接单步并保持暂停。
            self.assertEqual(frame((77,))[1], 1)
            self.assertEqual(state[2], 1)
            self.assertEqual(frame(), (0, 0))
            # 失焦按键与切回时仍按住的键都不触发。
            self.assertEqual(frame((78, 77), pid=99), (0, 0))
            self.assertEqual(frame((78, 77)), (0, 0))
            for _ in range(100):self.assertEqual(frame((78, 77)), (0, 0))
            self.assertEqual(frame(), (0, 0))
            # 原生禁止更新时不排队；下次解禁也不自动推进。
            old_steps = steps.value
            self.assertEqual(frame((77,), dt=0), (0, 0))
            self.assertEqual(steps.value, old_steps)
            self.assertEqual(frame(), (0, 0))
            self.assertEqual(frame((77,), dt=-0.033), (0, 0))
            self.assertEqual(frame(), (0, 0))
            state[0], state[1] = 117, 118
            self.assertEqual(frame((78, 77)), (0, 0))
            frame()
            self.assertEqual(frame((118,))[1], 1)
            frame()
            self.assertEqual(frame((117,))[1], 1)
            self.assertEqual(state[2], 0)
            frame()
            # 同时按下优先单步；非有效原生步长不执行。
            self.assertEqual(frame((117, 118))[1], 1)
            self.assertEqual(state[2], 1)
            frame()
            native_step.value = float('nan')
            self.assertEqual(frame((118,)), (0, 0))
        finally:
            self.k.VirtualFree(address, 0, 0x8000)

if __name__ == '__main__':
    unittest.main(verbosity=2)
