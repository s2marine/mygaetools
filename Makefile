.PHONY: server upload update

server:
	@dev_appserver.py --log_level debug .

upload:
	@appcfg.py update .

update:
	@pip2 install -r requirements.txt --upgrade -t lib

clean:
	@rm -rf lib/*
