from __future__ import annotations
import unittest
import os
from transilience.unittest import ChrootTestMixin
from transilience import actions


class TestApt(ChrootTestMixin, unittest.TestCase):
    def test_install_existing(self):
        res = list(self.system.run_actions([
            actions.Apt(
                name="Install dbus",
                pkg=["dbus"],
                state="present",
            )
        ]))

        self.assertEqual(len(res), 1)
        self.assertIsInstance(res[0], actions.Apt)
        self.assertFalse(res[0].changed)

    def test_install_missing(self):
        self.assertFalse(self.system.context.call(os.path.exists, "/usr/bin/hello"))

        res = list(self.system.run_actions([
            actions.Apt(
                name="Install cowsay",
                pkg=["hello"],
                state="present",
            )
        ]))

        self.assertTrue(self.system.context.call(os.path.exists, "/usr/bin/hello"))

        self.assertEqual(len(res), 1)
        self.assertIsInstance(res[0], actions.Apt)
        self.assertTrue(res[0].changed)
