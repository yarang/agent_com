# Product Overview

MCP Broker Server - Product documentation

---

## Product Identity

**Name:** MCP Broker Server
**Version:** 1.0.0
**Status:** Alpha
**License:** Apache-2.0
**Repository:** https://github.com/moai/mcp-broker-server

---

## Product Description

The MCP Broker Server is a centralized communication middleware that enables multiple Claude Code instances to discover each other, negotiate communication capabilities, and exchange messages. The server implements the Model Context Protocol (MCP) standard to provide tools that Claude Code instances can invoke.

### Problem Statement

Claude Code instances operate in isolation without a standard mechanism for:
- Discovering other instances on the same machine or network
- Negotiating compatible communication protocols
- Exchanging messages in a structured, reliable way

### Solution

The MCP Broker Server acts as an intermediary that:
- Maintains a registry of communication protocols with version tracking
- Tracks connected sessions with automatic health monitoring
- Performs automatic capability negotiation between sessions
- Routes messages using point-to-point and broadcast patterns
- Exposes all functionality through standard MCP tools

---

## Target Users

### Primary Users

1. **Claude Code Developers**
   - Integrating multiple Claude Code instances
   - Building multi-agent systems
   - Implementing inter-process communication

2. **System Administrators**
   - Deploying Claude Code infrastructure
   - Managing multi-instance deployments
   - Monitoring communication health

3. **Tool Builders**
   - Creating custom communication protocols
   - Building on top of MCP standard
   - Extending broker capabilities

### Use Cases

1. **Multi-Project Coordination**
   - Multiple Claude Code instances working on different projects
   - Cross-project communication and coordination
   - Shared resource access

2. **Multi-Agent Systems**
   - Specialized agents with different capabilities
   - Agent collaboration and delegation
   - Distributed problem solving

3. **Session Persistence**
   - Message queuing for offline recipients
   - Graceful handling of temporary disconnections
   - Reliable message delivery

4. **Protocol Evolution**
   - Versioned protocol definitions
   - Automatic compatibility checking
   - Gradual migration between versions

---

## Key Features

### Protocol Registry
- Register communication protocols with JSON Schema validation
- Semantic versioning for protocol evolution
- Protocol discovery with filtering
- Duplicate prevention

### Session Management
- Unique session ID assignment
- Automatic heartbeat monitoring
- Stale session detection and cleanup
- Message queuing for offline recipients

### Capability Negotiation
- Automatic compatibility checking
- Feature intersection identification
- Incompatibility reporting
- Upgrade suggestions

### Message Routing
- Point-to-point (1:1) messaging
- Broadcast (1:N) messaging
- Priority levels and TTL support
- Delivery confirmation and queuing

### Security
- Token-based authentication
- CORS protection
- Input validation
- Sensitive data redaction

### Storage Options
- In-memory storage for development
- Redis storage for distributed deployments
- Automatic failover to in-memory

---

## Value Proposition

### For Developers
- **Standardized Communication** - Use MCP tools without custom implementations
- **Type Safety** - Full Pydantic validation for all data structures
- **Easy Integration** - Simple configuration, clear API surface
- **Extensible** - Support for custom protocols and capabilities

### For Operators
- **Reliable** - Automatic health monitoring and message queuing
- **Observable** - Structured logging and HTTP status endpoints
- **Secure** - Built-in authentication and CORS protection
- **Scalable** - Optional Redis backend for distributed deployments

### For Organizations
- **Future-Proof** - Protocol versioning and compatibility checking
- **Standards-Based** - Built on official MCP specification
- **Open Source** - Apache 2.0 license for flexibility
- **Production Ready** - Security, logging, and deployment guides

---

## Competitive Advantages

1. **MCP Native** - Built from the ground up using the MCP standard
2. **Async-First** - Non-blocking I/O for high concurrency
3. **Storage Flexibility** - Choose between in-memory and Redis backends
4. **Capability Negotiation** - Automatic compatibility checking
5. **Security Built-In** - Authentication, validation, and CORS support

---

## Success Metrics

### Technical Metrics
- **Uptime** - 99.9% availability target
- **Latency** - < 100ms for local message delivery
- **Throughput** - 1000+ messages/second
- **Scalability** - 50+ concurrent sessions

### Quality Metrics
- **Test Coverage** - 85%+ target
- **Type Coverage** - 100% type hint coverage
- **Documentation** - Complete API and architecture docs
- **Security** - Zero known critical vulnerabilities

### Adoption Metrics
- **Integration** - Easy Claude Code integration
- **Onboarding** - < 30 minutes to first message
- **Community** - Active contributions and issues
- **Stability** - Alpha release with core features complete

---

## Roadmap

### Version 1.0 (Current)
- Core broker functionality
- In-memory storage
- Security module
- HTTP API
- MCP tools interface

### Version 1.1 (Planned)
- Protocol transformation adapters
- Dead-letter queue
- Rate limiting
- Improved test coverage (85%)

### Version 1.2 (Planned)
- Redis optimization
- Connection pooling
- Metrics and observability
- Admin dashboard

### Version 2.0 (Future)
- WebSocket support
- Multi-tenancy
- Message replay
- Advanced security features

---

## Related Documentation

- [Project Structure](structure.md) - Code organization and layout
- [Technical Stack](tech.md) - Technologies and dependencies
- [README.md](../../README.md) - Project overview and quick start
- [API Reference](../../docs/api.md) - Complete API documentation
