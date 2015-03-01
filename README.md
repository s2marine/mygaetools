# s2marine-gaetools
Some tools run on Google App Engine

## How to use
### 1. Install requirements
    $ make update
### 2. Add you own config
    $ cp rss/config.py.template rss/config.py
    $ vim rss/config.py
### 3. Add you own appid
    $ cp app.yaml.template app.yaml
    $ vim app.yaml
### 3. Upload to GAE
    $ make upload

## Read More
[rss](rss)

## License
This is licensed under the [GPL 3.0 license](LICENSE).
