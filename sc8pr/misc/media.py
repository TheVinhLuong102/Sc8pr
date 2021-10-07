# Copyright 2015-2021 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
#
# This file is part of "sc8pr".
#
# "sc8pr" is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "sc8pr" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "sc8pr".  If not, see <http://www.gnu.org/licenses/>.


import os, struct, pygame
from sc8pr import PixelData
from sc8pr.misc.video import Video


class Grabber:
    "A class for performing screen captures using PIL.ImageGrab.grab"
    
    def __init__(self, grab, rect=None):
        self.grab = grab
        if rect and not isinstance(rect, pygame.Rect):
            if len(rect) == 2: rect = (0, 0), rect
            rect = pygame.Rect(rect)
        self.rect = rect

    @property
    def bbox(self):
        "Bounding box for capture"
        r = self.rect
        if r: return [r.left, r.top, r.right, r.bottom]

    @property
    def pil(self): return self.grab(self.bbox)

    @property
    def pix(self): return PixelData(self.grab(self.bbox))

    @property
    def img(self): return self.pix.img


class ImageIO:
    "Use imageio and ffmpeg to decode and encode video"
    
    @staticmethod
    def init(im, np, pil=None, ffmpeg=None):
        ImageIO.im = im
        ImageIO.np = np
        ImageIO.pil = pil
        if ffmpeg: os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg

    @staticmethod
    def decode(src, *args, progress=None):
        "Load a movie file as a list of Video clips"
        if not args: args = (0,),
        vid = [Video() for a in args]
        with ImageIO.im.get_reader(src) as reader:
            meta = reader.get_meta_data()
            i, n = 1, meta.get("nframes")
            for v in vid:
                v.ffmpeg_meta = meta
                v.size = meta["size"]
                v.meta["frameRate"] = meta["fps"]
            v = 0
            info = struct.pack("!3I", 0, *vid[0].size)
            a = args[0]
            try: # Extra frames/bad metadata in MKV?
                for f in reader:
                    if len(a) == 2 and a[1] == i:
                        v += 1
                        if v >= len(args): break
                        a = args[v]
                    if i >= a[0]: vid[v] += bytes(f), info
                    if progress: progress(i, n)
                    i += 1
            except: pass
        return vid if args and len(args) > 1 else vid[0]

    @staticmethod
    def decodeSave(src, dest=None, size=512):
        "Convert a video file to s8v format"
        if dest is None: dest = src + ".s8v"
        ImageIO.decode(src, vid=Video().autoSave(dest, size)).autoSave()
        return dest

    @staticmethod
    def frameData(img):
        "Format frame data for imageio export"
        if ImageIO.pil:
            return ImageIO.np.array(img.pil(ImageIO.pil.Image.frombytes))
        img = pygame.surfarray.array3d(img.srf)
        return ImageIO.np.swapaxes(img, 0, 1)

    @staticmethod
    def encode(vid, dest="movie.mp4", fps=None, progress=None):
        "Encode a movie from a Video instance or s8v file"
        if type(vid) is str: vid = Video(vid)
        vid = vid.scaleFrames()
        i, n = 1, len(vid)
        if fps is None: fps = vid.meta.get("frameRate")
        if fps is None: fps = 30
        with ImageIO.im.get_writer(dest, fps=fps) as writer:
            for img in vid.frames():
                writer.append_data(ImageIO.frameData(img))
                if progress:
                    progress(i, n)
                    i += 1
