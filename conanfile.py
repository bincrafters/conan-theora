import os
import stat
from conans import ConanFile, MSBuild, AutoToolsBuildEnvironment, tools


class TheoraConan(ConanFile):
    name = "theora"
    version = "1.1.1"
    description = "Theora is a free and open video compression format from the Xiph.org Foundation"
    url = "https://github.com/bincrafters/conan-theora"
    homepage = "https://github.com/xiph/theora"
    topics = ("conan", "theora", "video", "video-compressor", "video-format")
    license = "BSD-3-Clause"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    requires = (
        "ogg/1.3.4",
        "vorbis/1.3.7"
    )
    _source_subfolder = "source_subfolder"
    _autotools = None

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def source(self):
        source_url = "http://downloads.xiph.org/releases/theora/libtheora-%s.zip" % self.version
        sha256 = "f644fef154f7a80e7258c8baec5c510f594d720835855cddce322b924934ba36"
        tools.get(source_url, sha256=sha256)
        extracted_dir = 'lib' + self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

        with tools.chdir(os.path.join(self._source_subfolder, 'lib')):
            # file somehow missed in distribution
            tools.download('https://raw.githubusercontent.com/xiph/theora/master/lib/theora.def', 'theora.def')
            assert "56362ca0cc73172c06b53866ba52fad941d02fc72084d292c705a1134913e806" == tools.sha256sum('theora.def')

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
        if self.settings.compiler == 'Visual Studio':
            self._build_msvc()
        else:
            with tools.chdir(self._source_subfolder):
                autotools = self._configure_autotools()
                autotools.make()

    def _build_msvc(self):
        # error C2491: 'rint': definition of dllimport function not allowed
        tools.replace_in_file(os.path.join(self._source_subfolder, 'examples', 'encoder_example.c'),
                              'static double rint(double x)',
                              'static double rint_(double x)')

        def format_libs(libs):
            return ' '.join([l + '.lib' for l in libs])

        # fix hard-coded library names
        project = 'libtheora'
        config = "dynamic" if self.options.shared else "static"

        vcvproj = '%s_%s.vcproj' % (project, config)
        vcvproj_path = os.path.join(self._source_subfolder, 'win32', 'VS2008', project, vcvproj)
        tools.replace_in_file(vcvproj_path,
                                'libogg.lib',
                                format_libs(self.deps_cpp_info['ogg'].libs), strict=False)
        tools.replace_in_file(vcvproj_path,
                                'libogg_static.lib',
                                format_libs(self.deps_cpp_info['ogg'].libs), strict=False)
        tools.replace_in_file(vcvproj_path,
                                'libvorbis.lib',
                                format_libs(self.deps_cpp_info['vorbis'].libs), strict=False)
        tools.replace_in_file(vcvproj_path,
                                'libvorbis_static.lib',
                                format_libs(self.deps_cpp_info['vorbis'].libs), strict=False)
        if "MT" in self.settings.compiler.runtime:
            tools.replace_in_file(vcvproj_path, 'RuntimeLibrary="2"', 'RuntimeLibrary="0"')
            tools.replace_in_file(vcvproj_path, 'RuntimeLibrary="3"', 'RuntimeLibrary="1"')

        with tools.chdir(os.path.join(self._source_subfolder, 'win32', 'VS2008')):
            target = 'libtheora' if self.options.shared else 'libtheora_static'
            sln = 'libtheora_dynamic.sln' if self.options.shared else 'libtheora_static.sln'
            msbuild = MSBuild(self)
            msbuild.build(sln, platforms={'x86': 'Win32', 'x86_64': 'x64'}, targets=[target])

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
