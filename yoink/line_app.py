from __future__ import division, print_function
from collections import OrderedDict

from yoink.widgets import (DeformableLine, ShutterCrop, NothingWidget,
                           CroppedImage)

import numpy as np
from matplotlib.widgets import RadioButtons, Button
import matplotlib.pyplot as plt


class LinePicker(object):
    def __init__(self, pixels, path):
        self.sel_fig, self.sel_axes = self.create_selector_figure()
        self.ann_fig, self.ann_axes = self.create_annotate_figure()

        self.select_image = self.sel_axes['img'].imshow(pixels)

        self.cropper = ShutterCrop(self.sel_axes['img'])
        self.cropper.active = False
        self.cropper.set_visible(True)

        self.cropped_img = CroppedImage(self.ann_axes['img'], pixels)
        self.cropped_img.make_xyextent_textboxes(self.ann_axes['xlo'],
                                                 self.ann_axes['xhi'],
                                                 self.ann_axes['ylo'],
                                                 self.ann_axes['yhi'])
        self.cropper.on_changed(self.cropped_img.crop)

        line_kw = dict(linewidth=0.5, color='k', alpha=0.5)
        circle_kw = dict(radius=15, alpha=0.5)
        self.line_picker = DeformableLine(self.sel_axes['img'],
                                          grows=True, shrinks=True,
                                          line_kw=line_kw, circle_kw=circle_kw)
        self.line_picker.active = False
        self.line_picker.set_visible(True)

        self.shadow_line = ShadowLine(self.ann_axes['img'],
                                      self.line_picker,
                                      self.cropper,
                                      marker='o', markersize=15, **line_kw)
        self.line_picker.on_changed(self.shadow_line.update)
        self.cropper.on_changed(self.shadow_line.update)

        line_kw = dict(lw=0)
        circle_kw = dict(radius=10, color='k')
        self.point_picker = DeformableLine(self.sel_axes['img'],
                                           grows=True, shrinks=True,
                                           line_kw=line_kw,
                                           circle_kw=circle_kw,
                                           )
        self.point_picker.active = False
        self.point_picker.set_visible(True)
        # shadow data plotted in axes coordiates
        self.shadow_points = ShadowLine(self.ann_axes['img'],
                                        self.point_picker,
                                        self.cropper,
                                        marker='o', markersize=10, **line_kw)
        self.point_picker.on_changed(self.shadow_points.update)
        self.cropper.on_changed(self.shadow_points.update)

        # the xlim/ylim may have changed due to adding the lines
        # set xlim/ylim to the pre-lines-added state
        extent = self.select_image.get_extent()
        self.select_image.axes.set_xlim(extent[:2])
        self.select_image.axes.set_ylim(extent[2:])

        extent = self.cropped_img.image.get_extent()
        self.cropped_img.ax.set_xlim(extent[:2])
        self.cropped_img.ax.set_ylim(extent[2:])

        self.create_selector_toggle()

        self.dump_button = Button(self.ann_axes['dump'], 'Dump to file')
        self.dump_func = self.dump_npz
        self.dump_button.on_clicked(self.dump)

        self.path = path

    def create_selector_toggle(self):
        self.selector_widgets = OrderedDict()
        self.selector_widgets['Do nothing'] = NothingWidget()
        self.selector_widgets['Crop'] = self.cropper
        self.selector_widgets['Segmented Line'] = self.line_picker
        self.selector_widgets['Manual Points'] = self.point_picker

        self.toggle_state('Do nothing')

        self.select_radio = RadioButtons(self.sel_axes['select'],
                                         labels=self.selector_widgets.keys(),
                                         active=0)
        self.select_radio.on_clicked(self.toggle_state)

    def toggle_state(self, new_state):
        """Change the active selector widget"""
        assert new_state in self.selector_widgets
        for k in self.selector_widgets:
            if k == new_state:
                continue
            self.selector_widgets[k].active = False
        self.selector_widgets[new_state].active = True

    def create_selector_figure(self, gut=0.04, sepx=0.01, wide=0.2, tall=0.3,
                               **ax_kwargs):
        fig = plt.figure()
        axes = {}

        x0 = gut + wide + sepx
        x1 = 1 - (gut + sepx)

        y0 = gut
        y1 = 1 - gut

        l, b = x0, y0
        w, h = x1 - x0, y1 - y0
        img = fig.add_axes([l, b, w, h], **ax_kwargs)
        img.yaxis.set_visible(False)
        img.xaxis.set_visible(False)
        axes['img'] = img

        l, b = gut, 0.5 * (y0 + y1 - tall)
        w, h = wide, tall
        select = fig.add_axes([l, b, w, h], **ax_kwargs)
        select.yaxis.set_visible(False)
        select.xaxis.set_visible(False)
        axes['select'] = select

        return fig, axes

    def create_annotate_figure(self, gut=0.04, sepx=0.05, sepy=0.04,
                               wide=0.09, tall=0.06,
                               **ax_kwargs):
        fig = plt.figure()
        axes = {}

        x0 = gut + wide + sepx
        x1 = 1 - (gut + sepx)

        y0 = gut + tall + sepy
        y1 = 1 - gut

        l, b = x0, y0
        w, h = x1 - x0, y1 - y0
        axes['img'] = fig.add_axes([l, b, w, h], **ax_kwargs)

        sizes = {}
        sizes['yhi'] = (gut, 1-gut-tall, wide, tall)
        sizes['ylo'] = (gut, gut+tall+sepy, wide, tall)
        sizes['xlo'] = (x0, gut, wide, tall)
        sizes['xhi'] = (x1-wide, gut, wide, tall)
        sizes['dump'] = (x0+wide+sepx, gut, x1-x0-2*(sepx+wide), tall)

        for name, lbwh in sizes.iteritems():
            ax = fig.add_axes(lbwh, **ax_kwargs)
            ax.yaxis.set_visible(False)
            ax.xaxis.set_visible(False)
            axes[name] = ax

        return fig, axes

    def get_data(self):
        data = {}
        data['x'] = None
        data['y'] = None
        raise NotImplemented
        return data

    def dump_npz(self):
        data = self.get_data()
        print('dumping to', self.path)
        np.savez(self.path, **data)
        print('dumped')

    def dump_txt(self):
        data = self.get_data()
        print('dumping to %s.*.txt' % self.path)
        for key, val in data:
            np.savetxt('%s.%s.txt' % (self.path, key), val)
        print('dumped')

    def dump(self, event):
        self.dump_func()
