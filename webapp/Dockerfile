FROM python:3.12-slim

# The whole service is stdlib — nothing to install. We ship the engine
# files next to the webapp so the image is self-contained from this repo.
WORKDIR /srv

COPY webapp/ /srv/webapp/
COPY a11yaudit.py a11yevidence.py a11ybadge.py a11yfix.py contrast.py \
     declaracion.py a11ydom.py a11ydiff.py a11ycrit.py a11ysarif.py \
     a11ybudget.py a11yscroll.py a11yvalidate.py arialive_js.py /srv/

# analizador.py inserts the PARENT of webapp/ into sys.path — inside the
# image that parent is /srv, which is exactly where the engine lives.
EXPOSE 8080
HEALTHCHECK --interval=60s --timeout=5s \
  CMD python3 -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/badge?score=1',timeout=4)"

CMD ["python3", "/srv/webapp/analizador.py", "--port", "8080"]
