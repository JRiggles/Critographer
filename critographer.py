import math
import tkinter as tk
import tkinter.filedialog as fd
from contextlib import suppress
# from tkinter import ttk
# from pathlib import Path
from PIL import ImageTk


# TODO: select map from file
# TODO: map panning
# TODO: better handling of rulers (adding, deleting, etc.)
# TODO: figure out proper DPI and scaling (1 square == 1" in real life!)
# TODO: zoom adjust (aim for automatic scaling, maybe add input for grid scale)
# TODO: toolbar (floating window so it's not on the main screen?)
# TODO: AoE shapes, colors
# nice to have:
# tokens, initiative tracker, fog of war

class Critographer(tk.Tk):
    """D&D Map Viewer"""
    def __init__(self):
        super().__init__()
        self.geometry(
            f'{self.winfo_screenwidth()}x{self.winfo_screenheight()}'
        )
        self.minsize(640, 480)
        self.attributes('-fullscreen', True)
        self.title('Critographer')
        self.update()  # force update to ensure fullscreen
        # init canvas  # FIXME: cursor isn't changing
        self.canvas = tk.Canvas(self, background='whitesmoke', cursor='cross')
        self.canvas.pack(expand=True, fill='both')
        # event bindings
        self.canvas.bind('<Button-1>', self.start_stop_line)
        self.canvas.bind('<Motion>', self.draw_line)
        # init empty set to store canvas items
        self.saved_drawings = set()
        self.line_start = (0, 0)

        # load background
        self.img_file = fd.askopenfilename(
            defaultextension='jpg',
            filetypes=[('Image files', '.gif .jpg .jpeg .png')],
        )
        self.img = ImageTk.PhotoImage(file=self.img_file)
        self.canvas.create_image(
            int(self.canvas.winfo_width() / 2),
            int(self.canvas.winfo_height() / 2),
            anchor='nw',
            tags='background_map',
            image=self.img,
        )
        self.saved_drawings = self.saved_drawings.union(
            set(self.canvas.find_withtag('background_map'))
        )

    def start_stop_line(self, event) -> None:
        if not all(self.line_start):
            self.line_start = (event.x, event.y)
        else:
            # save the latest line to the canvas
            self.saved_drawings = self.saved_drawings.union(
                set(self.canvas.find_withtag('line'))
            )
            self.line_start = (None, None)
            self.canvas.bind('<Button-2>', self.delete_item)

    def draw_line(self, event) -> None:
        """
        Draw a line starting at `self.line_start` and ending at the mouse pos.
        """
        if all(self.line_start):
            line_length = self.get_line_length()
            self.clear_frame()
            self.canvas.create_line(
                self.line_start[0],  # type: ignore
                self.line_start[1],  # type: ignore
                event.x,
                event.y,
                capstyle='round',
                fill='#5566FF',
                smooth=True,
                tags='line',
                width=5,
            )
            self.canvas.create_text(  # show line info
                event.x + 25,
                event.y + 25,
                fill='whitesmoke',
                font=('Times New Roman', 26,),
                tags='ruler_text',
                text=line_length,
            )
            ruler_text_bbox = self.canvas.bbox(
                self.canvas.find_withtag('ruler_text')[0]
            )
            self.canvas.create_rectangle(
                *ruler_text_bbox,
                fill='#222',
                outline='#222',
                tags='ruler_bubble',
                width=5,  # use outline to pad text bubble
            )
            self.canvas.tag_raise('ruler_text')
            self.canvas.unbind('<Button-2>')

    def clear_frame(self) -> None:
        """Clear previously drawn frames"""
        for item in self.canvas.find_all():
            if item not in self.saved_drawings:
                self.canvas.delete(item)

    def delete_item(self, event, tolerance: int = 5) -> str | None:
        """Delete the canvas item within `tolerance` units of the event"""
        # FIXME: delete lines one at a time, prevent deleting background
        line = self.canvas.find_overlapping(
            event.x - tolerance,
            event.y - tolerance,
            event.x + tolerance,
            event.y + tolerance,
        )[0]
        # self.canvas.delete(line)
        self.canvas.delete('!background_map')
        with suppress(IndexError):
            latest_text = self.canvas.find_withtag('ruler_text')[-1]
            self.canvas.delete(latest_text)

    def get_line_length(self) -> str:  # type: ignore
        """Return line length in feet"""
        # FIXME: get actual DPI value, length is off by a few decimals
        self.display_dpi = 100.0
        with suppress(IndexError):
            latest_line = self.canvas.find_withtag('line')[-1]
            x1, y1, x2, y2 = self.canvas.bbox(latest_line)
            length = round(math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2), 1)
            return f'{length / self.display_dpi * 5:.01f} feet'


if __name__ == '__main__':
    app = Critographer()
    app.mainloop()
