blendseg
========

A few python files which are helping me to do 3d segmentation in Blender.

Currently I am running this on a laptop with Core i5 Processor and a mesh with approximately 28000 faces. After initialization, it takes anywhere from 0.15-0.25s to complete the intersection and rendering operations. Optimization is on-going.

I'm still trying to figure out the Blender API. Currently I'm using Blender 2.63 on 64-bit Ubuntu 12.04.3.
Currently this is NOT working correctly with Blender 2.68 Ubuntu. Fix is in the works.

blender 2.62 (Ubuntu 12.04 repository version) -- Does not work

Blender 2.63a -- works

Blender 2.68 -- sort of works but position of contours needs to be fixed.

The newest version has had the collision detection rewritten, and so no longer uses Witold's code.

It uses a Quad-edge mesh representation for quickly constructing contours, and an AABB-Collision tree for fast collision detection.

--------------------------
This is all mostly based on some other projects. 

Blendseg was originally based on Witold Jaworski's intersection code:
http://airplanes3d.net/scripts-253_e.xml

It was rewritten in Oct 2013 to use quad-edge mesh representation and AABB collision tree to speed up calculations.

I can't remember where I dug up the create-plane-with-image code, but I'll try to find it.
