## 개발환경 세팅
### VS Code setting.json

- flake8
- black
- Extension: cweijan.vscode-mysql-client2

```json
{
    "python.linting.flake8Enabled": true,
    "python.linting.flake8Args": [
        "--max-line-length=100"
    ],
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "100"]
}
```

### DB

```bash
# create a container
$ docker run --name fastapi-db \
-p 3306:3306 \
-e MYSQL_ROOT_PASSWORD=1234 \
-e MYSQL_USER=admin \
-e MYSQL_PASSWORD=1234 \
-d mysql:8.0 \
--character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

# check
$ docker exec -it fastapi-db mysql -uroot -p
```

```sql
mysql> GRANT ALL ON *.* TO admin@'%';
mysql> SHOW GRANTS FOR admin@'%';
# 또는 admin 접속 중이라면
mysql> SHOW GRANTS FOR CURRENT_USER();
mysql> CREATE DATABASE dev;
mysql> SHOW DATABASES;
```
