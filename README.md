xsheet - traditional 2D animation
=================================

What this app aims to be
------------------------

A FLOSS application for creating traditional 2D animation, the digital
way.  It can be added in the production pipeline of feature films,
videogames, and other audiovisual projects.  Uses raster (pixel)
graphics and features MyPaint's brushlib.

What this app will not be
-------------------------

- No vector drawings, as this app is for traditional 2D animation.
  For Flash-like cut-out animation, try other apps like Synfig.  You
  can add this app in your vector animation pipeline using it for
  making pencil sketches, then exporting and vectorizing.

- Not for post-production.  But this app should consider that the
  post-production will be done in another app.  The export should be
  suitable to import in other apps as image sequence, like Blender.

Development
-----------

The code is written in the Python language, using the GTK+ stack
through introspection.  Uses the fantastic MyPaint brushes, brushlib,
and GEGL for graphics operations.

Milestone 1: simple flipbook
----------------------------

- A canvas to draw in.

- Two tools: pen and eraser.

- Add Frame button: adds frame next to the current one.

- Simple light table: always on, show two preview frames in
  transparency.

- Play in loop.

- Resize brush.

- Clean Frame button.

Milestone 2: same functionality as the MyPaint animation fork
-------------------------------------------------------------

- Timeline.  Horizontal widget that shows the frames and allow
  navigation.  This wasn't in the fork but is a must.

- X-sheet that allows animating in twos or in ones, separation of work
  doing the keyframes first and the inbetweens later.  And reusage of
  cels.

- Playback controls.

- Configurable light table.

- Load/Save animation in custom format, ORA derivative.

- Export animation as sequence of images with specified format.

- Brush and color selectors.

Milestone 3: things we missed in the animation fork
---------------------------------------------------

- Animation layers.

- Sketch pencil that allows sketching in the same layer of the final
  drawing, using a different stroke color.  Draw with a brush whose
  strokes can be dismissed later.  This is like the blue pencil in
  traditional animation.

- Floodfill tool or paint bucket.  With configurable threshold to
  allow holes in the line drawing.  Allow fill in a layer different
  than the layer that contains the line drawing.

- Camera frame with default sizes.  This doesn't limit the drawing to
  its bounds, but allows to draw considering the final view of the
  camera.  Allow display safe area and configurable grid for movement
  reference and proportions.  The camera data can be exported in a
  data file.

- Export: output registration frame together with the image sequence.
  This is for visual registration of animation layers in
  post-production apps.  This can be a peg-holes graphic or maybe a
  simple cross.

- Export: output registration data together with the image sequence.
  This is for automatic registration of animation layers in
  post-production apps.  The import function in the post-production
  app should be able to read this data and automatically place the
  sequence.

- Audible metronome.  For animating in tempo.  The tempo could change
  at any point of the animation.

Milestone 4: audio and animation improvements
---------------------------------------------

- Audio insertion.  For animating in sync with an audio track, like
  lip-sync animation.

- Timeline widget add-on: show the audio waveform.  Do it by default,
  can be hidden in the preferences.

- Scrub a range of cels in current layer.  Similar to flipping the
  pages in traditional animation.

- Walkcycles functionality.  Select a range of frames in the current
  animation layer and mark an offset.  The range is repeated N times,
  displaced by the offset.  This is like using the pegbars to displace
  the paper cels for making walkcycles in traditional animation.

Future ideas
------------

- Playback using a proxy video.

- Timeline widget add-on: allow to draw sketches inside.

- Import video as animation layer for rotoscoping.

- Export improvement: instead of exporting huge images all the same
  size, export the cels sequence together with their offsets in a json
  data file.  The import function in the post-production apps should
  be adapted to read this.

- Maybe add multiplane camera.  Althrough this app is not meant for
  post-production, having a simple implementation of a multiplane
  camera may do the previsualization easier.  If this is the case, the
  multiplane camera data can be exported as a json data file and the
  import function of the post-production apps should be adapted to
  read it.
