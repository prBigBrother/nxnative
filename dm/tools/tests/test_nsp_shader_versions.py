"""A registered code build outside shader_versions needs its own shaders, even when both updates are present. No game files or tools are needed."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'dm/games')); sys.path.insert(0, str(REPO / 'dm/tools'))
import game, nacp, profile_guess
spec = importlib.util.spec_from_file_location('nsp_shader_versions', REPO / 'scripts/build_ipa_from_nsp.py')
assert spec is not None and spec.loader is not None
nsp = importlib.util.module_from_spec(spec); spec.loader.exec_module(nsp)
nsp.__dict__.update(pg=profile_guess, nacp=nacp)   # main initializes these dependencies in CLI runs
ID, OLD, NEW = '0100AAAA00000000', 'ab' * 16, 'cd' * 16


class ShaderVersions(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.root = Path(tmp.name)
        self.prof = self.root / 'games' / ID; self.prof.mkdir(parents=True)
        self.text = (f'title_id\t{ID}\nprogram_id\t{ID}\nname\tTest\nmodules\tmain\n'
                     f'build\tv262144\t1.0.5\tmain={OLD}\nbuild\tv327680\t1.0.6\tmain={NEW}\n'
                     'package\tv327680\nshader_versions\tv327680\nstdalloc_cap\t0xa4000000\n')
        (self.prof / 'game.tsv').write_text(self.text)
        (self.prof / 'shader_map.tsv').write_text('# newer shaders must not be copied into the older package\n')
        self.g = game.Game(self.prof)

    def test_older_registered_build_derives_its_shaders_with_both_updates_present(self):
        have = {'v0', 'v262144', 'v327680'}
        self.assertTrue(nsp.shader_profile_reason(self.g, 'v262144', have))
        self.assertFalse(nsp.shader_profile_reason(self.g, 'v327680', have))
        data = self.root / 'extract'; (data / 'ExeFS').mkdir(parents=True)
        (data / 'ExeFS/main').write_bytes(b'NSO0' + bytes(0x3c) + bytes.fromhex(OLD) + bytes(0x50))
        (data / 'control.nacp').write_bytes(bytes(0x3060) + b'1.0.5' + bytes(0x1000))
        out = self.root / 'derived' / ID
        with mock.patch.object(nsp, 'say', lambda m: None), mock.patch.dict(os.environ, {'DM_GAMES_DIR': str(self.prof.parent)}):
            nsp.derive_profile(self.g, out, 'v262144', data, ['main'])
        g = game.Game(out)
        self.assertEqual(g.words('shader_versions'), ['v262144'])
        self.assertEqual(g.builds()['v262144']['main'], OLD)
        self.assertEqual(g.builds()['v262144']['display'], '1.0.5')
        self.assertEqual(g.get('stdalloc_cap'), '0xa4000000')
        self.assertFalse((out / 'shader_map.tsv').exists())

    def test_registered_union_keeps_its_tables_only_when_all_inputs_are_present(self):
        (self.prof / 'game.tsv').write_text(self.text.replace('shader_versions\tv327680', 'shader_versions\tv262144 v327680'))
        g = game.Game(self.prof)
        self.assertFalse(nsp.shader_profile_reason(g, 'v262144', {'v262144', 'v327680'}))
        self.assertTrue(nsp.shader_profile_reason(g, 'v262144', {'v262144'}))

    def test_unregistered_package_still_derives(self):
        self.assertTrue(nsp.shader_profile_reason(self.g, 'v393216', {'v327680', 'v393216'}))

    def test_profile_with_no_shader_versions_keeps_existing_selection(self):
        (self.prof / 'game.tsv').write_text(self.text.replace('shader_versions\tv327680', 'shader_versions\t'))
        self.assertFalse(nsp.shader_profile_reason(game.Game(self.prof), 'v262144', {'v262144'}))


if __name__ == '__main__':
    unittest.main()
