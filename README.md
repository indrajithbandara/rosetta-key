# Digital Rosetta Stone Key Website

This repository has the website infrastructure for the original keys (master files) for [FileFormat.Info](https://www.fileformat.info/)'s Digital Rosetta Stone project.

Due to size constraints, some of the actual files themselves are not in git.  You need to download them directly from the website.

Files not in repo:
 
 * settlement
 * firstflight
 * earthrise
 * adultschool

The [rosetta-www repository](https://github.com/fileformat/rosetta-www) has the code for the main [www.digitalrosetta.org](https://www.digitalrosetta.org/) website, which has
nice pages with thumbnails and human-readable descrptions.

## Tips

To get the files without the year prefix: `rename 's/^[0-9]{4}-//' *`
