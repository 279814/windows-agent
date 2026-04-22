from desktop_agent_dev.mcp_server import create_server


def test_manifest_is_available() -> None:
    server = create_server()
    manifest = server.manifest

    assert manifest["name"] == "desktop-agent-dev"
    assert manifest["readme_uri"] == "desktop-agent-dev://readme"
    assert manifest["catalog_uri"] == "desktop-agent-dev://catalog"
    assert manifest["capabilities_uri"] == "desktop-agent-dev://capabilities"
    assert manifest["security_uri"] == "desktop-agent-dev://security"
    assert manifest["tool_count"] == len(server.tool_registry.specs)


def test_readme_catalog_capabilities_security_resources_exist() -> None:
    server = create_server()

    assert server.readme["title"] == "Desktop Agent Dev Workspace"
    assert server.readme["sections"][0]["heading"] == "Purpose"
    assert server.catalog["title"] == "Desktop Agent Tool Catalog"
    assert server.catalog["sections"][1]["heading"] == "Content"
    assert server.capabilities["title"] == "Desktop Agent Capabilities"
    assert server.security["title"] == "Desktop Agent Security"
    assert len(server.catalog["content"]["groups"]) >= 1
    assert len(server.catalog["content"]["tools"]) == len(server.tool_registry.specs)


def test_tool_handbook_has_formal_directory_sections() -> None:
    server = create_server()
    handbook = server.tool_handbook

    assert handbook["title"] == "Desktop Agent Tool Handbook"
    section_headings = [section["heading"] for section in handbook["sections"]]
    assert section_headings == ["Overview", "Tool Catalog", "Capabilities", "Security"]


# def test_server_registers_resources_when_supported() -> None:
#     server = create_server()
#
#     assert hasattr(server.mcp, "_resources")
#     assert [item["name"] for item in server.mcp._resources] == ["readme", "catalog", "capabilities", "security", "manifest", "tool-handbook", "tool-index"]
