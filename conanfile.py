#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import stat
from conans import ConanFile, MSBuild, AutoToolsBuildEnvironment, tools


class TheoraConan(ConanFile):
    name = "theora"
    version = "1.1.1"
    description = "Theora is a free and open video compression format from the Xiph.org Foundation"
    url = "https://github.com/bincrafters/conan-theora"
    homepage = "https://github.com/xiph/theora"
    author = "Bincrafters <bincrafters@gmail.com>"
    topics = ("conan", "theora", "video", "video-compressor", "video-format")
    license = "BSD-3-Clause"
    exports = ["LICENSE.md"]
    exports_sources = "theora.patch"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    requires = (
        "ogg/1.3.3@bincrafters/stable",
        "vorbis/1.3.6@bincrafters/stable"
    )
    _source_subfolder = "source_subfolder"
    _autotools = None

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def configure(self):
        del self.settings.compiler.libcxx

    def source(self):
        source_url = "http://downloads.xiph.org/releases/theora/libtheora-%s.zip" % self.version
        sha256 = "f644fef154f7a80e7258c8baec5c510f594d720835855cddce322b924934ba36"
        tools.get(source_url, sha256=sha256)
        extracted_dir = 'lib' + self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def _configure_autotools(self):
        if not self._autotools:
            permission = stat.S_IMODE(os.lstat("configure").st_mode)
            os.chmod("configure", (permission | stat.S_IEXEC))
            self._autotools = AutoToolsBuildEnvironment(self, win_bash=tools.os_info.is_windows)
            configure_args = ['--disable-examples']
            if self.options.shared:
                configure_args.extend(['--disable-static', '--enable-shared'])
            else:
                configure_args.extend(['--disable-shared', '--enable-static'])
            self._autotools.configure(args=configure_args)
        return self._autotools

    def build(self):
        tools.patch(base_path=self._source_subfolder, patch_file="theora.patch")
        if self.settings.compiler == 'Visual Studio':
            self._build_msvc()
        else:
            with tools.chdir(self._source_subfolder):
                autotools = self._configure_autotools()
                autotools.make()

    def _build_msvc(self):
        with tools.chdir(os.path.join(self._source_subfolder, 'win32', 'VS2008')):
            sln = 'libtheora_dynamic.sln' if self.options.shared else 'libtheora_static.sln'
            msbuild = MSBuild(self)
            msbuild.build(sln, upgrade_project=True, platforms={'x86': 'Win32', 'x86_64': 'x64'})

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        if self.settings.compiler == 'Visual Studio':
            include_folder = os.path.join(self._source_subfolder, "include")
            self.copy(pattern="*.h", dst="include", src=include_folder)
            self.copy(pattern="*.dll", dst="bin", keep_path=False)
            self.copy(pattern="*.lib", dst="lib", keep_path=False)
        else:
            with tools.chdir(self._source_subfolder):
                autotools = self._configure_autotools()
                autotools.install()

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
