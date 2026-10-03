# Running Hermes with Ollama

Hermes can use Ollama as its model provider. The quickest way to install,
configure, and start Hermes is:

```bash
ollama launch hermes
```

> The launcher is interactive. Run it from a terminal where Ollama is installed
> and the local Ollama service is available.

## Before you start

1. Install Ollama for your operating system.
2. Start Ollama if it is not already running:

   ```bash
   ollama serve
   ```

3. Optionally pull a local model in advance:

   ```bash
   ollama pull <model-name>
   ```

## Launch and configure Hermes

Run the launcher:

```bash
ollama launch hermes
```

The guided setup may:

1. Offer to install Hermes when it is not already installed.
2. Ask you to choose an Ollama model.
3. Create or update the Hermes configuration to use Ollama's
   OpenAI-compatible endpoint at `http://127.0.0.1:11434/v1`.
4. Offer to configure an optional messaging gateway.
5. Start a Hermes chat session.

Choose a model that is available to your Ollama installation and appropriate
for the memory and compute available on your machine. The models presented by
the launcher can change as Ollama and Hermes evolve.

## Reconfigure Hermes

Use the Hermes setup commands if you want to revisit configuration after the
initial launch:

```bash
# Run the complete setup wizard again.
hermes setup

# Configure or update a messaging integration.
hermes gateway setup
```

Hermes stores its user configuration under `~/.hermes/`. Treat files in that
directory as sensitive: gateway credentials and other secrets should never be
committed to this repository.

## Troubleshooting

### `hermes` is not found

Run `ollama launch hermes` again and accept the installation prompt. If the
installation fails, follow the current installation instructions in the
[Hermes Agent repository](https://github.com/NousResearch/hermes-agent).

### A local model is missing

Pull it before relaunching Hermes:

```bash
ollama pull <model-name>
ollama launch hermes
```

You can inspect locally installed models with:

```bash
ollama list
```

### Ollama is unreachable

Confirm that the server is running and that its API responds:

```bash
ollama serve
curl http://127.0.0.1:11434/api/tags
```

If Ollama is already managed as a system service, do not start a second
instance; check the service status instead.

### A messaging gateway is not responding

Run `hermes gateway setup` again and verify the credentials for the selected
provider. Keep tokens and passwords in the Hermes environment or secret store,
not in source control.

## References

- [Ollama's Hermes integration guide](https://docs.ollama.com/integrations/hermes)
- [Hermes Agent source and installation instructions](https://github.com/NousResearch/hermes-agent)
