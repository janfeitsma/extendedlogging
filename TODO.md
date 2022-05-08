## extendedlogging

* when an exception occurs, produce ERROR event and close the tracing properly
* also trace pid/tid, consistent with ttviewer
* fix timezone handling, just log it (see fibonacci demo)

## ttviewer

* consider what to do with incomplete trace files
* consider what to do when logged timestamps are equal
* ttfilter tool to select time range
* improve instant event visualization
* file merge mode
* pid/tid support
* consider rewriting some parsers in C++ for speed
* ttparse: bugfix CALL/RETURN mixup


