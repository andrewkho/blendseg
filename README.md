blendseg
========

A few python files which are helping me to do 3d segmentation in Blender.

Currently I am running this on a laptop with Core i5 Processor and a mesh with approximately 28000 faces.
It is now fast enough to update contours interactively! 


I'm still trying to figure out the Blender API. Currently I'm using Blender 2.68 on 64-bit Ubuntu 12.04.3. 

After changing the mesh by sculpting, the user must enter and exit EDIT mode (by hitting the tab-key twice in succession) in order to notify BlendSeg that the mesh's vertices and bounding boxes must be updated. This is a hack because Blender currently does not raise a flag after scupting is done. A suggestion by the folks on #blenderdev at freenode is to use a Null modifier on the sculpt (terminology?) in order to raise the update flag.


Status of tested Blender versions:
==================
October 2013:

Blender 2.62 (Ubuntu 12.04 repository version) -- Does not work

Blender 2.63a -- works

November 2013:

Blender 2.68 -- works



Implementation details:
====================
The newest version has had the collision detection rewritten, and so no longer uses Witold's code.

It uses a Quad-edge mesh representation for quickly constructing contours, and an AABB-Collision tree for fast collision detection.

This project owes some debt to Witold Jaworski's intersection code, found at 
http://airplanes3d.net/scripts-253_e.xml

However, the current code no longer uses Witold's implementation and was re-written to address the specific needs and constraints of this project. It was rewritten in Oct 2013 to use quad-edge mesh representation and AABB collision tree to speed up calculations.

