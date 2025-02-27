Honyaku
=======

Translate po-files using Gengo.com

Installation
============

1. Create a virtual env.
2. `pip install '.'`

Usage
=====

Honyaku uses the Gengo API with two states:

1. It creates a translation job and writes the id in the targeted PO file.
2. It checks the job id and displays each translation for manual acceptance.

To use, store your GENGO public/private key in the following variables. Notice the single quotes:

```shell
export GENGO_PUBLIC_KEY='your public key'
export GENGO_PRIVATE_KEY='your private key'
```

Afterwards initiate a new job as follows:

```shell
honyaku <path-to-po-file> <source-language> <target-language> \
  --tone "formal" --limit 100 --tier standard
```

The limit is recommended to avoid creating thousands of jobs in case Honyaku
does something wrong.

Optionally, a command can be sent to the translator:

```shell
honyaku foo.po en fr \
  --tone "formal" --limit 100 --tier standard \
  --commend "Text between ${} and {} are variables and should be left alone"
```

Once a job has been sent, it's status can be queried by running the same
exact command again. Once a translation is available, it has to be accepted
(if it's okay) or refused (with a comment).

Limitations
===========

Note that there are a lot of HTTPS warnings at the moment, due to this bug:
https://github.com/gengo/gengo-python/issues/99

In the future we should probably simply use our own REST client.

License
-------
honyaku is released under GPLv2
