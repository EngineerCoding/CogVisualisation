# CogVisualisation
Visualises COGs stored in PostgreSQL database as created by https://github.com/EngineerCoding/BPCogs-2016-2017. Currently
this is programmed to only take input from the specified database, but can be abstracted to use multiple input sources. An
example for this can be the input stream for the program, but that is beyond the scope of this project. There is no point
in abstracting this yet until different scripts are used to generate COGs and images are needed as output.


Program arguments can be found by running:
```
python3 visualise_cog.py -h
```

A dependency for this program is Pillow:
```
python3 -m pip install pillow
```
