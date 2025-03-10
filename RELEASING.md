- Generate yaml dump from excel: python import_protocol_doc.py ISCP_AVR_146.xlsx > eiscp-commands.yaml
- Regenerate commands.py: python generate_commands_module.py eiscp-commands.yaml > eiscp/commands.py

 - Split command files out for xml: python split-commands-yaml.py

- Edit CHANGES
- Increase version in setup.py.
- Commit & git tag -a
- par
