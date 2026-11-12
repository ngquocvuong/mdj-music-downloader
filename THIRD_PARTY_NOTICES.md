# Third-Party Notices

MDJ Music Downloader's own source code is licensed under the [MIT License](LICENSE).

The ready-to-install packages (the `.deb` and the program built with `./build.sh`) also contain
software made by others. Each part keeps its own license, listed below.

## Important: GPL parts in the packaged program

The packaged program includes **mutagen** (GPL-2.0-or-later) and, through Pillow, the system
libraries **libimagequant** (GPL-3.0-or-later) and **jbigkit** (GPL-2.0-or-later). Because of
this, the packaged program as a whole is distributed under the terms of the
**GNU General Public License, version 3 or later**. MDJ's own source code stays under the MIT
License, which is compatible with the GPL.

The complete source code for the packaged program is available:

- **MDJ Music Downloader:** this repository, at the tag of each release
  (for example `v1.1.2`): https://github.com/ngquocvuong/mdj-music-downloader
- **Python packages** (mutagen, customtkinter, darkdetect, Pillow, packaging, typing_extensions):
  the exact versions on https://pypi.org, and Ubuntu 22.04's source packages
- **System libraries** (libimagequant, jbigkit, Tcl/Tk, OpenSSL and the others listed below):
  the Ubuntu 22.04 (jammy) source packages, https://packages.ubuntu.com/jammy
- **yt-dlp and Deno:** see their sections below

If any of these sources stops being available, ask at
https://github.com/ngquocvuong/mdj-music-downloader/issues and a copy will be provided.

The full text of the GPL is at https://www.gnu.org/licenses/gpl-3.0.html. On Debian, Ubuntu and
Linux Mint it is also in `/usr/share/common-licenses/GPL-3` (and GPL-2 next to it).

## Programs shipped next to the app

| Program | License | Source |
|---|---|---|
| **yt-dlp** (standalone build `yt-dlp_linux`) | The Unlicense (public domain); its bundled parts are listed in yt-dlp's `THIRD_PARTY_LICENSES.txt` | https://github.com/yt-dlp/yt-dlp |
| **Deno** | MIT (text below) | https://github.com/denoland/deno |
| **ffmpeg** | LGPL-2.1+ / GPL-2+ | Not shipped in the `.deb`: installed from your distribution (`Depends: ffmpeg`) |

## Python and libraries inside the app

| Component | License |
|---|---|
| Python 3.10 | Python Software Foundation License (PSF-2.0) |
| Tcl/Tk 8.6 (tkinter) | Tcl/Tk license (BSD-style) |
| CustomTkinter 5.2.2 | MIT (text below) |
| darkdetect 0.8.0 | BSD-3-Clause (text below) |
| mutagen | GPL-2.0-or-later |
| Pillow | HPND (text below) |
| packaging | Apache-2.0 or BSD-2-Clause |
| typing_extensions | PSF-2.0 |
| libimagequant | GPL-3.0-or-later |
| jbigkit (libjbig) | GPL-2.0-or-later |
| OpenSSL 3 | Apache-2.0 |
| zlib, libpng, libjpeg, libtiff, libwebp, openjpeg, freetype, fontconfig, expat, libffi, brotli, zstd, xz, bzip2, mpdecimal, libdeflate, libbsd, libmd, libuuid, X11 libraries, libgomp | Permissive licenses (zlib, MIT, BSD, IJG, FreeType) or GPL with the GCC runtime exception (libgomp); see each library's `/usr/share/doc/<package>/copyright` on Ubuntu |
| PyInstaller bootloader | GPL-2.0-or-later with the PyInstaller exception (allows any license for the bundled program) |

---

## License texts

### Deno

```
MIT License

Copyright 2018-2026 the Deno authors

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

### CustomTkinter

```
MIT License

Copyright (c) 2023 Tom Schimansky

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### darkdetect

```
Copyright (c) 2019, Alberto Sottile
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of "darkdetect" nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL "Alberto Sottile" BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### Pillow (HPND)

```
The Python Imaging Library (PIL) is

    Copyright © 1997-2011 by Secret Labs AB
    Copyright © 1995-2011 by Fredrik Lundh and contributors

Pillow is the friendly PIL fork. It is

    Copyright © 2010 by Jeffrey A. Clark and contributors

Like PIL, Pillow is licensed under the open source HPND License:

By obtaining, using, and/or copying this software and/or its associated
documentation, you agree that you have read, understood, and will comply
with the following terms and conditions:

Permission to use, copy, modify and distribute this software and its
documentation for any purpose and without fee is hereby granted,
provided that the above copyright notice appears in all copies, and that
both that copyright notice and this permission notice appear in supporting
documentation, and that the name of Secret Labs AB or the author not be
used in advertising or publicity pertaining to distribution of the software
without specific, written prior permission.

SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR BE LIABLE FOR ANY SPECIAL,
INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
```

### yt-dlp

yt-dlp is released into the public domain under The Unlicense:
https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE. The standalone `yt-dlp_linux` build bundles
Python and other libraries; their licenses are listed in `THIRD_PARTY_LICENSES.txt` on each
yt-dlp release page: https://github.com/yt-dlp/yt-dlp/releases
