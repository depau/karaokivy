How to make a theme for Karaokivy
=================================

1. Grab the source of the default theme.
2. Replace the images with your custom ones.
3. Using a command line, run the following command:

$ python gen_kk_theme.py <themedir>

The gen_kk_theme.py script is in the tools directory.

The theme directory should contain one directory for every atlas.
Inside every atlas directory there should be at least one of the following directories:
 * include - contains all the images that should be included in the atlas as they are, without modification
 * stack - contains images that should be automatically stacked: every image in the fg subdirectory will be put on every image in bg, then put in the atlas with the following name: fg_bg
Every directory can contain a "noinclude" directory, that will be ignored.