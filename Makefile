apply:
	cd infra/ && terraform apply
up:
	docker compose -f local/docker-compose.yaml up -d
down:
	docker compose -f local/docker-compose.yaml down
