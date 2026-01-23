# ghstats2

ghstats2 is an update to ghstats, to be written by Claude code.  

# ghstats

The original ghstats was intended for tracking user interest in the FLORIS repo.  It was based on older python packages and an assumption of a server based postgres server to hold results.  Several of the old files from ghstats are in source_files.

# what is expected of ghstats2

1) Tracks the following repos: 
 - https://github.com/NatLabRockies/floris
 - https://github.com/NatLabRockies/flasc
 - https://github.com/NatLabRockies/hercules
 - https://github.com/NatLabRockies/hycon
 - https://github.com/NatLabRockies/ROSCO

2) Updates the approaches used in ghstats to use modern capabilities to both track user downloads, forks, clones and does a better job disambiguating repeat users versus new users, new clones, uniques etc.

3) Google analytics.  All 4 repos have google analytics tagged in their docs page on github pages (for example https://natlabrockies.github.io/floris/).  This repo finds ways to merge information from there with the basic github information.

4) We no longer presume an external database.  A simple file is updated within the repo and committed.

5) Following more current practices, uv, ruff, pyproject.toml are all used here.

6) A more modern, either notebook or html file are provided to overview results.  It is more possible to compare across repos.  It is easy to add new repos, rename, remove etc.

