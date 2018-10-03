#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, MSBuild, AutoToolsBuildEnvironment, tools
import os


class TheoraConan(ConanFile):
    name = "theora"
    version = "1.1.1"
    description = "Theora is a free and open video compression format from the Xiph.org Foundation"
    url = "https://github.com/bincrafters/conan-theora"
    homepage = "https://www.theora.org/"
    author = "Bincrafters <bincrafters@gmail.com>"
    license = "BSA"
    exports = ["LICENSE.md"]
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = "shared=False", "fPIC=True"

    source_subfolder = "source_subfolder"
    build_subfolder = "build_subfolder"

    requires = (
        "ogg/1.3.3@bincrafters/stable",
        "vorbis/1.3.6@bincrafters/stable"
    )

    def config_options(self):
        del self.settings.compiler.libcxx
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def source(self):
        source_url = "http://downloads.xiph.org/releases/theora/libtheora-%s.zip" % self.version
        tools.get(source_url)
        extracted_dir = 'lib' + self.name + "-" + self.version
        os.rename(extracted_dir, self.source_subfolder)

        with tools.chdir(os.path.join(self.source_subfolder, 'lib')):
            # file somehow missed in distribution
            tools.download('https://raw.githubusercontent.com/xiph/theora/master/lib/theora.def', 'theora.def')

    def build(self):
        if self.settings.compiler == 'Visual Studio':
            self.build_msvc()
        else:
            self.build_configure()

    def build_msvc(self):
        # error C2491: 'rint': definition of dllimport function not allowed
        tools.replace_in_file(os.path.join(self.source_subfolder, 'examples', 'encoder_example.c'),
                              'static double rint(double x)',
                              'static double rint_(double x)')

        def format_libs(libs):
            return ' '.join([l + '.lib' for l in libs])

        # fix hard-coded library names
        for project in ['encoder_example', 'libtheora', 'dump_video']:
            for config in ['dynamic', 'static']:
                vcvproj = '%s_%s.vcproj' % (project, config)
                tools.replace_in_file(os.path.join(self.source_subfolder, 'win32', 'VS2008', project, vcvproj),
                                      'libogg.lib',
                                      format_libs(self.deps_cpp_info['ogg'].libs), strict=False)
                tools.replace_in_file(os.path.join(self.source_subfolder, 'win32', 'VS2008', project, vcvproj),
                                      'libogg_static.lib',
                                      format_libs(self.deps_cpp_info['ogg'].libs), strict=False)
                tools.replace_in_file(os.path.join(self.source_subfolder, 'win32', 'VS2008', project, vcvproj),
                                      'libvorbis.lib',
                                      format_libs(self.deps_cpp_info['vorbis'].libs), strict=False)
                tools.replace_in_file(os.path.join(self.source_subfolder, 'win32', 'VS2008', project, vcvproj),
                                      'libvorbis_static.lib',
                                      format_libs(self.deps_cpp_info['vorbis'].libs), strict=False)

        with tools.chdir(os.path.join(self.source_subfolder, 'win32', 'VS2008')):
            sln = 'libtheora_dynamic.sln' if self.options.shared else 'libtheora_static.sln'
            msbuild = MSBuild(self)
            msbuild.build(sln, upgrade_project=True, platforms={'x86': 'Win32', 'x86_64': 'x64'})

    def build_configure(self):
        def chmod_plus_x(name):
            os.chmod(name, os.stat(name).st_mode | 0o111)
        with tools.chdir(self.source_subfolder):
            chmod_plus_x('configure')
            configure_args = []
            if self.options.shared:
                configure_args.extend(['--disable-static', '--enable-shared'])
            else:
                configure_args.extend(['--disable-shared', '--enable-static'])
            env_build = AutoToolsBuildEnvironment(self)
            if self.settings.os != 'Windows':
                if self.options.fPIC:
                    configure_args.append('--with-pic')
                env_build.pic = self.options.fPIC
            env_build.configure(args=configure_args)
            env_build.make()
            env_build.install()

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses", src=self.source_subfolder)
        self.copy(pattern="COPYING", dst="licenses", src=self.source_subfolder)
        if self.settings.compiler == 'Visual Studio':
            include_folder = os.path.join(self.source_subfolder, "include")
            self.copy(pattern="*.h", dst="include", src=include_folder)
            self.copy(pattern="*.dll", dst="bin", keep_path=False)
            self.copy(pattern="*.lib", dst="lib", keep_path=False)

    def package_info(self):
        if self.settings.compiler == 'Visual Studio':
            self.cpp_info.libs = ['libtheora' if self.options.shared else 'libtheora_static']
        else:
            self.cpp_info.libs = ['theora']
