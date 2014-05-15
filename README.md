xsheet - draw traditional 2D animation
======================================

Current state
-------------

This application is in early development.  Testing is encouraged.  If
you are interested, please drop me a line.

About
-----

**xsheet** is a FLOSS application for drawing traditional 2D
animation, the digital way.  The kind of workflow it allows is known
as "paperless", because it replaces the traditional light box.  It can
be added in the production pipeline of feature films, videogames, and
other audiovisual projects.

The name **xsheet** comes from the good ol' days: an
[X-sheet](http://en.wikipedia.org/wiki/Exposure_sheet) is a
spreadsheet that allows an animation team to organize the
work. Animating "on twos" or "on ones", marking the key drawings,
doing the inbetweens later, setting the tempo to sync the characters
with the music.

This application works with raster (pixel) graphics.  For vector
animation you can try other applications like Synfig.  You can add
this application in your vector animation pipeline using it for making
pencil sketches, then exporting and vectorizing.

Current features
----------------

- multiple layers
- onion skinning
- playback
- metronome

Development
-----------

The code is written in the Python language, using the GTK+ stack and
other libraries through GObject introspection.  It relies in the
following great libraries:

- [GEGL](http://www.gegl.org/) as backend

- GEGL-gtk ([source](https://git.gnome.org/browse/gegl-gtk/),
  [docs](http://www.gegl.org/gegl-gtk/)) as GEGL display

- [MyPaint brushlib](http://wiki.mypaint.info/Development/Documentation/Brushlib)
  as brush engine, MyPaint GEGL Surface as drawing canvas

Ideas
-----

- Sketch pencil that allows sketching in the same layer of the final
  drawing, using a different stroke color.  Draw with a brush whose
  strokes can be dismissed later.  This is like the blue pencil in
  traditional animation.

- Floodfill tool (paint bucket).  With configurable threshold to allow
  holes in the line drawing.  Allow fill in a layer different than the
  layer that contains the line drawing.

- Camera frame with default sizes.  This doesn't limit the drawing to
  its bounds, but allows to draw considering the final view of the
  camera.  Allow display safe area and configurable grid for movement
  reference and proportions.

- Audio insertion.  For animating in sync with an audio track, like
  lip-sync animation.  Show the audio waveform.

- Scrub frames with trackpad scroll.  Similar to flipping the pages in
  traditional animation.

- Walkcycles functionality.  Select a range of frames in the current
  animation layer and mark an offset.  The range is repeated N times,
  displaced by the offset.  This is like using the pegbars to displace
  the paper cels for making walkcycles in traditional animation.

- Import video as animation layer for rotoscoping.
