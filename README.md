RAG with LangChain

In the rapidly evolving landscape of artificial intelligence, Retrieval-Augmented Generation (RAG) stands out as an useful approach combining the strength of information retrieval with the power of generative language models. This approach enhances the ability of models to generate more accurate, informative, and contextually relevant responses by incorporating external knowledge sources during the generation process.

In order to showcase this system we will deploy an application capable of uploading documents to a vector store, previous calculation of embeddings.Our interface will provide an interactive chat which will take our query and via semantic search retrieve the most relevant documents available in our vector store. Finally the resulting prompt composed of both the initial query and the retrieved information is fed to the LLM in order to form an informed response.

We will help ourselves in the development of this application with the Langchain framework, which provides tools and interfaces for vector store operations, prompt construction and LLM interaction.

## AWS Infrastructure

Starting with the vector database, we are going to deploy an OpenSearch cluster. To lower costs we will stick with one `t3.small.search` instance, as it will suffice for testing purposes.

```tf
resource "aws_opensearch_domain" "this" {
  depends_on = [time_sleep.await_role_propagation]

  domain_name    = local.app_name
  engine_version = "OpenSearch_2.11"

  cluster_config {
    dedicated_master_enabled = false
    instance_count           = 1
    instance_type            = "t3.small.search"
    zone_awareness_enabled   = false
  }

  ebs_options {
    ebs_enabled = true
    iops        = 3000
    throughput  = 125
    volume_size = 20
    volume_type = "gp3"
  }

  vpc_options {
    subnet_ids = [
      data.aws_subnets.public.ids[0],
    ]

    security_group_ids = [aws_security_group.opensearch.id]
  }

  advanced_options = {
    "rest.action.multi.allow_explicit_index" = "true"
  }

  access_policies = data.aws_iam_policy_document.this.json
}

```

The streamlit application in `src` folder will be packaged into a docker image and uploaded to the Elastic Container Registry (ECR). From there it will be ready to be deployed as service in Elastic Container Service (ECR).

```tf
resource "aws_ecr_repository" "this" {
  name = local.app_name
}

resource "null_resource" "build_image" {

  depends_on = [
    aws_ecr_repository.this
  ]

  triggers = {
    always_run = "${timestamp()}"
  }

  provisioner "local-exec" {
    command = (templatefile("${path.module}/build_image.tpl", {
      aws_account_id = data.aws_caller_identity.current.account_id,
      region         = data.aws_region.current.name,
      repository_url = aws_ecr_repository.this.repository_url,
      image_tag      = "latest",
      source         = "${local.root_path}/src/"
      }
    ))
  }
}
```

For simplicity, both the application and infrastructure will be built and deployed together. The docker build is performed in the `terraform apply` operation by calling a bash script via the null resource

```bash
cd ${source}
aws ecr get-login-password --region ${region} | docker login  \
    --username AWS \
    --password-stdin ${aws_account_id}.dkr.ecr.${region}.amazonaws.com
docker build --build-arg CLOUD_PROVIDER=aws --platform linux/amd64 -t ${repository_url}:${image_tag} . 
docker push ${repository_url}:${image_tag}
```

We will reference the image uploaded to the registry in our ECS Task Definition, with Fargate being the capacity provider of choice for this showcase application. We make sure to map the correct port for Streamlig (`8501` being the default) and provide the necessary environment variables to connect to our OpenSearch cluster.

```tf
resource "aws_ecs_task_definition" "this" {
  depends_on = [null_resource.build_image]

  family = local.app_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "2048"

  task_role_arn = aws_iam_role.ecs_task_role.arn
  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([{
    name  = local.app_name
    image = "${aws_ecr_repository.this.repository_url}:latest"
    essential = true
    portMappings = [{
      containerPort = 8501
      hostPort      = 8501
      protocol      = "tcp"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.this.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "ecs"
      }
    }
    environment = [
      {
        name  = "AWS_REGION"
        value = data.aws_region.current.name
      },
      {
        name  = "OPENSEARCH_ENDPOINT"
        value = "https://${aws_opensearch_domain.this.endpoint}:443"
      },
      {
        name  = "OPENSEARCH_INDEX_NAME"
        value = local.app_name
      },
      {
        name  = "CLOUD_PROVIDER"
        value = "aws"
      }
    ]
  }])
}
```

With the Task Definition out of the way, we can create the ECS Service. As mentioned before we have opted to run our application in Fargate, and just one container instance for the demoing purposes. The service will have two security groups attached; one to allow internet access (to call OpenAI api) and the OpenSearch user security group.

```tf
resource "aws_ecs_service" "this" {
  name            = local.app_name
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = data.aws_subnets.public.ids
    security_groups = [aws_security_group.ecs_sg.id, aws_security_group.opensearch_user.id]
    assign_public_ip = true
  }

  load_balancer {
    container_port = 8501
    container_name = jsondecode(aws_ecs_task_definition.this.container_definitions)[0].name
    target_group_arn = aws_lb_target_group.this.arn
  }
}
```

Finally, the service will be fronted by an Application Load Balancer will give us a public IP and DNS to reach our application from the internet.

```tf
resource "aws_lb" "this" {
  name               = local.app_name
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.public.ids
}

resource "aws_lb_target_group" "this" {
  name        = local.app_name
  port        = 80
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.this.id
  target_type = "ip"
}

resource "aws_lb_listener" "this" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this.arn
  }
}
```

### Streamlit Application

First thing our application will do is retrieve the configuration from the environment variables for the appropiate cloud provider we are using, AWS in our case. In addition it will retrieve the embeddings model and instantiate the vector store using the aforementioned embeddings model. Finally it will create the Streamlit interface components.

```python
class StreamlitInterface:
    def __init__(self):
        self.cfg = Config.from_env()
        self.embeddings = build_embeddings_model()
        self.vector_store = build_provider_vector_store(
            cfg=self.cfg,
            embeddings=self.embeddings,
        )

        SidePanel(self.vector_store)
        MainPanel(self.vector_store)
```

For our embeddings model we will use `all-mpnet-base-v2` from `SBERT`. This model is downloaded and invoked locally so there is no cost associated with embedding calculations, apart from the instance we are provisioning for the application.


```python
def build_embeddings_model():
   model_name = "sentence-transformers/all-mpnet-base-v2"
   model_kwargs = {'device': 'cpu'}
   encode_kwargs = {'normalize_embeddings': False}
   return HuggingFaceEmbeddings(
       model_name=model_name,
       model_kwargs=model_kwargs,
       encode_kwargs=encode_kwargs
   )
```

Then we instantiate the vector store. As our application is developed with the intention of being platform agnostic, it will create the appropiate vector store for the cloud provider specified. In this scenario, we will create a connection to our OpenSearch cluster.

```python
def build_provider_vector_store(
    cfg: Config,
    embeddings: Embeddings
):
    if cfg.cloud_provider == CloudProvider.AWS:
        from streamlit_app.vector.opensearch import build_opensearch_store

        if not isinstance(cfg.provider_cfg, AWSConfig):
            raise TypeError(f"Expected AWSConfig for AWS provider, got {type(cfg.provider_cfg).__name__}")

        return build_opensearch_store(
            cfg=cfg,
            aws_cfg=cfg.provider_cfg,
            embeddings=embeddings
        )

    ...
```

In our side panel we will provide the user with the option to upload files into the vector store. For the fun of it we also included a small control panel to modify text chunking parameters, in case we want to play around with different configurations.

```python
class SidePanel:
    ...
    
    def upload_button_impl(self, uploaded_files: list[UploadedFile]| None):
        if uploaded_files:
            try:
                documents = transform_files_to_documents(uploaded_files)
                chunked_documents = chunk_documents(documents, self.chunk_size, self.chunk_overlap)
                self.vector_store.add_documents(chunked_documents)
                st.success(f"Uploaded {len(uploaded_files)} files successfully!")
            except Exception as e:
                st.error(f"There was a problem uploading files: {e}")
        else:
            st.sidebar.write("Please upload a file.")

    ...
```

--- Include an image?

Going a bit deeper into the details of the Langchain framework, we need to turn the uploaded files into Documents. This is an type provided by Langchain and getting this out of the way will allow us to work seamlessly with the rest of functionalities provided by the framework. Immediately after that we can chunk our documents with the provided parameters. Like that, the uploaded files are ready to be ingested in OpenSearch with `self.vector_store.add_documents(chunked_documents)`

```python
def transform_files_to_documents(
    uploaded_files: list[UploadedFile],
):
    documents = []
    for uploaded_file in uploaded_files:
        content = uploaded_file.read().decode("utf-8")
        doc = Document(page_content=content, metadata={"filename": uploaded_file.name})
        documents.append(doc)

    return documents

def chunk_documents(documents: list[Document], chunk_size: int = 1000, chunk_overlap: int = 30):
   text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
   return text_splitter.split_documents(documents)
```

Moving to our main panel, where we will have the chatbot. First thing we do is create an empty chat history, where we will store the whole conversation with the LLM. --- more blablabla

```python
class MainPanel:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

        st.header("Chat with GPT with your own RAG")

        if not os.getenv("OPENAI_API_KEY"):
            st.warning("Please enter an API Key to use the ChatBot")
        else:
            self.__init_message_history()
            self.__build_chatbot()


    def __init_message_history(self):
        if "messages" not in st.session_state:
            st.session_state["messages"] = []

    def __build_chatbot(self):
        rag_chain = build_rag_chain(self.vector_store)

        for message in st.session_state["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if not self.vector_store:
            st.error("There was a problem instantiating Vector Store")

        if prompt := st.chat_input("Enter your question here.."):
            st.session_state["messages"].append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                response = rag_chain.invoke(prompt)
                st.session_state["messages"].append({"role": "assistant", "content": response})
                st.write(response)
```

Note  `rag_chain = build_rag_chain(self.vector_store)`. Then we just call it along with the user prompt in `response = rag_chain.invoke(prompt)` and retrieve the system response. It is in this Langchain pipeline where the magic resides.


```python
def build_rag_chain(vector_store: Any):
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    llm = ChatOpenAI(model="gpt-3.5-turbo-0125")

    if not vector_store:
        prompt = build_chatbot_prompt(rag=False)
        return (
            {"question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )


    prompt = build_chatbot_prompt(rag=True)
    retriever = vector_store.as_retriever()
    return (
        {"context": retriever | format_docs | log_document, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
```

As we can see the pipeline consists of a few parts. First we construct a composite prompt with the elements `context` and `question`. Langchain allows you to use the vector store as a VectorStoreRetriever to seamlessly retrieve the relevants documents from the database employing the user's prompt. This two elements are inserted in the parametrized prompts we have created, depending if we are using RAG or not.

```python
def build_chatbot_prompt(rag: bool = False):
    rag_prompt=PromptTemplate(
        input_variables=["context", "question"],
        template="""
            Answer the following question making use of the given context.
            If you don't know the answer, just say you don't know.

            -----------------
            Question:
            {question}

            -----------------
            Context:
            {context}
        """
    )

    no_rag_prompt=PromptTemplate(
        input_variables=["question"],
        template="""
            Answer the following question.
            If you don't know the answer, just say you don't know.

            -----------------
            Question:
            {question}
        """
    )

    if rag:
        prompt = rag_prompt
        input_variables=["context", "question"]
    else:
        prompt = no_rag_prompt
        input_variables=["question"]

    return ChatPromptTemplate(
        input_variables=input_variables,
        messages=[HumanMessagePromptTemplate(prompt=prompt)]
    )
```

All that is left is passing our prompt to the LLM, where we have opted for GPT 3.5 Turbo, and retrieving the response as a string. This pipeline can be executed just by doing `rag_chain.invoke(prompt)` as we can notice in the `MainPanel` module.


-- Insert image here ---






## Deployment

Application can be deployed with
```bash
make apply
```

## Local development

A local OpenSearch can be deployed and dismantled

```bash
make up
make down
```

Install the dependencies with

```bash
pip install -r requirements.txt
```

Run the application with the appropiate environment variables using

```bash
python local/run_streamlit.py
```
