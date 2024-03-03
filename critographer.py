import tkinter as tk
import tkinter.filedialog as fd
from contextlib import suppress
from math import sqrt
from tkinter import ttk

import pymonctl as pmc
# from pathlib import Path
from PIL import Image, ImageTk

# TODO: improve selecting map from file
# TODO: better handling of rulers (adding, deleting, etc.)
# TODO: zoom adjust (aim for automatic scaling, maybe add input for grid scale)
# TODO: toolbar
# TODO: AoE shapes, colors
# IDEA: minimap on primary display
# nice to have:
# tokens, initiative tracker, fog of war

# TODO: figure out how to get image DPI when it's not available in Image.info
IMG_DPI = 100  # this is temporary...


class Critographer(tk.Tk):
    """D&D Map Viewer"""
    def __init__(self) -> None:
        super().__init__()
        self.geometry(
            f'{self.winfo_screenwidth()}x{self.winfo_screenheight()}'
        )
        self.minsize(640, 480)
        self.attributes('-fullscreen', True)
        self.title('Critographer')
        self.update()  # force update to ensure fullscreen

        # self.toolbar = Toolbar(self)

        self.displays = pmc.getAllMonitorsDict()
        print(self.displays)
        self.display_dpi = 144
        self.ui_scale_factor = 2.00
        # grid scale ratio in inches per foot (default: 1" = 5')
        self.map_grid_ratio = (1, 5)  # TODO: use this properly

        # init canvas
        self.canvas = tk.Canvas(self, background='#11111F', cursor='cross')
        self.canvas.pack(expand=True, fill='both')
        # set up scrolling
        self.scrollbar_x = ttk.Scrollbar(
            self,
            command=self.canvas.xview,
            orient='horizontal',
        )
        self.scrollbar_x.pack(fill='x', side='bottom')
        self.scrollbar_y = ttk.Scrollbar(
            self,
            command=self.canvas.yview,
            orient='vertical',
        )
        self.scrollbar_y.pack(before=self.canvas, fill='y', side='right')
        self.canvas.configure(
            xscrollcommand=self.scrollbar_x.set,
            yscrollcommand=self.scrollbar_y.set,
        )
        # event bindings
        self.bind('<Command-o>', self.load_map)  # open map
        self.canvas.bind('<Button-1>', self.start_stop_line)
        self.canvas.bind('<Motion>', self.draw_line)
        self.canvas.bind('<Button-3>', self.pan_start)
        self.canvas.bind('<B3-Motion>', self.pan_canvas)
        self.canvas.bind('<MouseWheel>', self.vscroll)  # vertical scroll
        self.canvas.bind('<Shift-MouseWheel>', self.hscroll)  # horiz. scroll
        self.canvas.bind('<Command-MouseWheel>', self.zoom_canvas)  # TODO
        # init line_start coords (placeholder)
        self.line_start = (0, 0)

        self.load_map()
        self.focus()

    def load_map(self, _event=None) -> None:
        scale = self.display_dpi / IMG_DPI
        if (
            img_file := fd.askopenfilename(
                defaultextension='jpg',
                filetypes=[('Image files', '.gif .jpg .jpeg .png')],
            )
        ):
            # init empty set to store canvas items
            self.saved_drawings = set()
            # delete previous map, if any
            self.canvas.delete('background_map')
            with Image.open(img_file) as img:
                width, height = img.size
                img = img.resize(
                    (int(scale * width), int(scale * height)),
                    resample=Image.Resampling.LANCZOS
                )
                self.img = ImageTk.PhotoImage(img)
            background_map = self.canvas.create_image(
                int(self.canvas.winfo_width() / 2),
                int(self.canvas.winfo_height() / 2),
                anchor='nw',
                tags='background_map',
                image=self.img,
            )
            self.canvas.config(  # prevent panning outside of map area
                scrollregion=self.canvas.bbox('background_map')
            )
            self.save_drawings((background_map,))

    def save_drawings(self, canvas_items: tuple[int, ...]) -> None:
        self.saved_drawings = self.saved_drawings.union(canvas_items)

    def start_stop_line(self, event) -> None:
        if not all(self.line_start):
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            self.line_start = (x, y)
        else:
            # save the latest line to the canvas
            self.save_drawings(self.canvas.find_withtag('line'))
            self.line_start = (None, None)
            self.canvas.tag_bind('line', '<Button-2>', self.delete_item)

    def draw_line(self, event) -> None:
        """
        Draw a line starting at `self.line_start` and ending at the mouse pos.
        """
        if all(self.line_start):
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            line_length = self.get_line_length()
            self.clear_frame()
            # draw a line to act as a ruler
            self.canvas.create_line(
                self.line_start[0],  # type: ignore
                self.line_start[1],  # type: ignore
                x,
                y,
                capstyle='round',
                fill='#5566FF',
                smooth=True,
                tags='line',
                width=5,
            )
            # show line length in ft
            self.canvas.create_text(
                x + 25,
                y + 25,
                fill='whitesmoke',
                font=('Big Caslon', 26,),
                tags='ruler_text',
                text=line_length,
            )
            ruler_text_bbox = self.canvas.bbox(
                self.canvas.find_withtag('ruler_text')[0]
            )
            # create background for text to improve readability
            self.canvas.create_rectangle(
                *ruler_text_bbox,
                fill='#222',
                outline='#222',
                tags='ruler_bubble',
                width=5,  # use outline to pad text bubble
            )
            # bring text to front
            self.canvas.tag_raise('ruler_text')
            # prevent right-click-delete while actively drawing
            self.canvas.tag_unbind('line', '<Button-2>')

    def clear_frame(self) -> None:
        """Clear previously drawn frames"""
        for item in self.canvas.find_all():
            if item not in self.saved_drawings:
                self.canvas.delete(item)

    def delete_item(self, event, tolerance: int = 5) -> str | None:
        """Delete the canvas item within `tolerance` units of the event"""
        item = self.canvas.find_closest(event.x, event.y, tolerance)[0]
        self.canvas.delete(item)
        with suppress(IndexError):
            # FIXME: only delete ruler info if associated line was selected
            text = self.canvas.find_withtag('ruler_text')[0]
            bubble = self.canvas.find_withtag('ruler_bubble')[0]
            self.canvas.delete(text, bubble)

    def get_line_length(self) -> str:  # type: ignore
        """Return line length in grid-scale feet (1 in:5 ft)"""
        # TODO: get image dpi programmatically, not all images provide this
        scale = self.display_dpi / IMG_DPI
        with suppress(IndexError):
            self.latest_line = self.canvas.find_withtag('line')[-1]
            x1, y1, x2, y2 = self.canvas.coords(self.latest_line)
            length_in_px = sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
            length_in_in = (
                length_in_px / (IMG_DPI * scale)
                # length_in_px / (self.display_dpi * self.ui_scale_factor)
            )
            return f'{length_in_in * 5:.01f} ft'

    def pan_start(self, event) -> None:
        """Store initial panning coords on middle-click"""
        self.canvas.scan_mark(event.x, event.y)

    def pan_canvas(self, event) -> None:
        """Pan the canvas by holding middle-click and moving"""
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def vscroll(self, event) -> str | None:
        if event.delta >= 1:
            self.canvas.yview_moveto(min(self.canvas.yview()) + 0.05)
        elif event.delta <= 1:
            self.canvas.yview_moveto(min(self.canvas.yview()) - 0.05)
        else:
            return 'break'

    def hscroll(self, event) -> str | None:
        if event.delta >= 1:
            self.canvas.xview_moveto(min(self.canvas.xview()) + 0.05)
        elif event.delta <= 1:
            self.canvas.xview_moveto(min(self.canvas.xview()) - 0.05)
        else:
            return 'break'

    def zoom_canvas(self, event) -> None:
        print(event)
        ...  # TODO


class Toolbar(tk.Toplevel):  # TODO
    def __init__(self, parent) -> None:
        """Critographer toolbar window"""
        super().__init__(parent)
        self.geometry('600x100')
        self.resizable(False, False)
        self.transient(parent)
        self.attributes('-alpha', 0.5)

        # toolbar items
        self.btn_open_file = ttk.Button(self, text='Open Map(s)')
        self.btn_open_file.pack(padx=5, pady=5)

        self.bind('<FocusIn>', lambda _e: self.attributes('-alpha', 1.0))
        self.bind('<FocusOut>', lambda _e: self.attributes('-alpha', 0.5))
        self.bind('<Enter>', lambda _e: self.attributes('-alpha', 1.0))
        self.bind('<Leave>', lambda _e: self.attributes('-alpha', 0.5))


if __name__ == '__main__':
    app = Critographer()
    app.mainloop()
