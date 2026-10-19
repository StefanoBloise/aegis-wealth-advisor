# Dependencies and attribution

- Python standard library: Python Software Foundation License.
- NumPy: BSD 3-Clause License, https://numpy.org/doc/stable/license.html
- SciPy: BSD 3-Clause License, https://scipy.org/license.html
- HiGHS (included through SciPy): MIT License, https://highs.dev/
- Optional video generation: Pillow (HPND), https://pillow.readthedocs.io/
- Optional video encoder: FFmpeg, license depends on the installed build and
  codec configuration. https://ffmpeg.org/legal.html
- Document generation: LaTeX and Beamer, installed separately. Consult the
  distribution's component licenses. No TeX distribution is bundled.
- Optional network service: OpenAI API, subject to the team's provider agreement.

No third-party market dataset, copied product facts, fonts or binary dependency
wheels are bundled. The synthetic generator and catalog are included in source.
The final MP4 embeds rasterized text, not font files. Do not infer that API
access, market data or fictional products are endorsed by the competition.

Standard mathematical foundations are cited in docs/01_technical.tex. The
Wasserstein reformulation is not claimed as novel. Original team attribution is
preserved; the team must verify ownership and the competition's independent-work
requirements before submission. This release was substantially refactored with
AI assistance and should be reviewed by the named entrants. No software license
for the team's own code is assigned without their decision.
