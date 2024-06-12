cd ${source}
aws ecr get-login-password --region ${region} | docker login --username AWS --password-stdin ${aws_account_id}.dkr.ecr.${region}.amazonaws.com
docker build --build-arg CLOUD_PROVIDER=aws --platform linux/amd64 -t ${repository_url}:${image_tag} . 
docker push ${repository_url}:${image_tag}
