# Internet Utilities

#### Features:
[Scrapper](#scrapper)
***

## Scrapper
This scrapper implements Selenium, Chromium Webdriver instance in order to take advantage of Javascript support.<br>
It combines two instances of the Chromium Webdriver; one if for accessing content on the TOR network and the other is via the default internet connection.<br>

The chosen of webdriver is determined based on the URL provided.  If the URL is for a '.onion' domain, it will auto choose the webdriver used for the TOR network.

Note: To utilise the TOR webdriver, you will require a TOR connection that supports the ability to proxy (http://torproject.org).

#### To use the scrapper:
```python
from digital_thought_commons.internet import scrapper

with scrapper.Scrapper() as scrapper_instance:
    scrapper_instance.get('pass url to obtain')
```

#### To enable Headless mode:
```python
from digital_thought_commons.internet import scrapper

with scrapper.Scrapper(headless=False) as scrapper_instance:
    scrapper_instance.get('pass url to obtain')
```

#### To specify path to Chromium Driver:<br>
Note: if you do not specify a path to the driver, it will look for it in the path.
```python
from digital_thought_commons.internet import scrapper

with scrapper.Scrapper(chromium_driver=r'./chromedriver') as scrapper_instance:
    scrapper_instance.get('pass url to obtain')
```

#### To force a URL to be obtained via the TOR network:
```python
from digital_thought_commons.internet import scrapper

with scrapper.Scrapper(chromium_driver=r'./chromedriver') as scrapper_instance:
    scrapper_instance.get('pass url to obtain', force_tor=True)
```

#### Specify TOR proxy details
Note: By default, the scrapper will configur the TOR webdriver instance with the following proxy details:
```
--proxy-server=socks5://127.0.0.1:9150
```
How to specify a different TOR proxy:
```python
from digital_thought_commons.internet import scrapper

with scrapper.Scrapper(tor_proxy='--proxy-server=socks5://127.0.0.1:9050') as scrapper_instance:
    scrapper_instance.get('pass url to obtain', force_tor=True)
```