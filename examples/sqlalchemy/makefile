.PHONY: build run

build:
	cd graphiql; npm install; npm run build

run:
	FLASK_APP=booksapp.server:app FLASK_ENV=development flask run
