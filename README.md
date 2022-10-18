## Git Docset

[Git](http://git-scm.com/docs) docset for [Dash](https://kapeli.com/dash) or [Zeal](https://zealdocs.org/).

Originally a fork of [git-dash](https://github.com/iamaziz/git-dash) but reworked and expanded in Python 3.

Option to build docset in any language supported by the [Git manpages translation project](https://hosted.weblate.org/projects/git-manpages/translations/) - pass the [ISO639-1/ISO3166-1 language/country code](https://github.com/datasets/language-codes/blob/master/data/ietf-language-tags.csv) as an argument to gendocset.py, e.g. python gendocset.py pt_BR<br>
The git-scm.com/docs convention appears to be:<br>
\<lowercase language code\>_[\<uppercase variant\>-]\<uppercase country code\><br>
e.g. zh_HANS-CN

NB Translations are incomplete for many languages. In such cases, the docset will be built with English as the fallback language for documents that are yet to be translated.

#### Screenshot
![Screenshot](./screenshot.png)
