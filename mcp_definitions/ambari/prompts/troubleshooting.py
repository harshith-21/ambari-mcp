from mcp.server.fastmcp import FastMCP

def register_prompts(mcp: FastMCP):
    """Register troubleshooting prompt templates with the MCP server"""
    
    @mcp.prompt("ambari-service-down-troubleshooting")
    async def service_down_troubleshooting(service_name: str, cluster_name: str) -> str:
        """Troubleshooting guide for when a service is down in Ambari.
        
        Args:
            service_name: Name of the service that is down
            cluster_name: Name of the cluster
        """
        return f"""# Troubleshooting Guide: {service_name} Service Down in {cluster_name}

## Initial Assessment
1. **Check Service Status**
   - Use: `get_service_health` tool to verify current state
   - Look for: Service state, maintenance mode, desired state
   - Expected: Service should be in 'STARTED' state

2. **Review Component Health**
   - Use: `get_component_health` tool with service_name="{service_name}"
   - Check: Individual component states and counts
   - Look for: Components in 'INSTALLED' state that should be 'STARTED'

3. **Check Host Health**
   - Use: `get_host_health` tool to verify all hosts are healthy
   - Look for: Hosts in unhealthy state or maintenance mode
   - Verify: Network connectivity and resource availability

## Common Issues and Solutions

### Issue 1: Service Components Not Started
**Symptoms:** Components show as 'INSTALLED' instead of 'STARTED'
**Solution:**
- Use `start_service` tool to start the entire service
- Or use `start_component` for individual components
- Check logs for startup errors

### Issue 2: Configuration Issues
**Symptoms:** Service fails to start after configuration changes
**Solution:**
- Use `get_service_config_versions` to review recent changes
- Use `rollback_service_config` to revert to a working version
- Verify configuration syntax and dependencies

### Issue 3: Resource Constraints
**Symptoms:** Components fail due to insufficient resources
**Solution:**
- Check host metrics using `get_cluster_metrics`
- Verify memory and CPU allocation in service configs
- Consider scaling up resources or optimizing configurations

### Issue 4: Dependency Services Down
**Symptoms:** Service depends on other services that are not running
**Solution:**
- Check all dependent services (e.g., HDFS for YARN, ZooKeeper for HBase)
- Start services in proper dependency order
- Use service checks to verify dependencies

## Step-by-Step Recovery Process

1. **Stop the Service** (if partially running)
   ```
   stop_service(server_url, "{cluster_name}", "{service_name}")
   ```

2. **Check and Fix Configuration** (if needed)
   ```
   get_service_config_versions(server_url, "{cluster_name}", "{service_name}")
   ```

3. **Start Dependencies First**
   - Identify and start any required services
   - Verify they are healthy before proceeding

4. **Start the Service**
   ```
   start_service(server_url, "{cluster_name}", "{service_name}")
   ```

5. **Run Service Check**
   ```
   run_service_check(server_url, "{cluster_name}", "{service_name}")
   ```

6. **Monitor and Verify**
   - Check service health after startup
   - Review alerts for any ongoing issues
   - Monitor for stability over time

## Prevention Tips
- Regular health checks and monitoring
- Proper maintenance windows for updates
- Configuration backups before changes
- Resource monitoring and capacity planning
- Keep services and dependencies updated

## Additional Resources
- Check Ambari server logs: `/var/log/ambari-server/`
- Check service-specific logs on host machines
- Review Ambari alerts for detailed error messages
- Use `get_request_status` to monitor operation progress
"""

    @mcp.prompt("ambari-performance-issues")
    async def performance_troubleshooting(cluster_name: str) -> str:
        """Troubleshooting guide for Ambari cluster performance issues.
        
        Args:
            cluster_name: Name of the cluster experiencing performance issues
        """
        return f"""# Performance Troubleshooting Guide for {cluster_name}

## Performance Assessment Checklist

### 1. Cluster Health Overview
- Use: `get_cluster_overview` resource to get overall cluster status
- Check: Service states, host health, alert summary
- Look for: Services in degraded state, unhealthy hosts, critical alerts

### 2. Resource Utilization Analysis
- Use: `get_cluster_metrics` tool to check system resources
- Monitor: CPU usage, memory utilization, disk I/O, network throughput
- Identify: Resource bottlenecks and saturation points

### 3. Service-Specific Performance
- Use: `get_service_health` for each critical service
- Check: Component response times, queue lengths, throughput metrics
- Focus on: HDFS, YARN, HBase performance indicators

## Common Performance Issues

### HDFS Performance Issues
**Symptoms:**
- Slow file operations
- High NameNode RPC queue times
- DataNode connectivity issues

**Investigation Steps:**
1. Check NameNode heap usage and GC patterns
2. Verify DataNode health and network connectivity
3. Review HDFS block replication and balancer status
4. Analyze client connection patterns

**Tools to Use:**
- `get_component_health` for HDFS components
- `get_cluster_metrics` for HDFS-specific metrics
- `get_alerts` filtered for HDFS alerts

### YARN Performance Issues
**Symptoms:**
- Job queue buildup
- Resource allocation problems
- Container launch delays

**Investigation Steps:**
1. Check ResourceManager health and capacity
2. Review NodeManager resource allocation
3. Analyze queue configurations and utilization
4. Verify application resource requests

### HBase Performance Issues
**Symptoms:**
- Slow read/write operations
- Region server failures
- Compaction backlogs

**Investigation Steps:**
1. Check RegionServer health and load distribution
2. Review HBase Master status and operations
3. Analyze region splits and compactions
4. Verify ZooKeeper connectivity

## Performance Optimization Actions

### Configuration Tuning
1. **Review Current Configurations**
   ```
   get_service_config(server_url, "{cluster_name}", "yarn-site")
   get_service_config(server_url, "{cluster_name}", "hdfs-site")
   ```

2. **Common Optimizations**
   - Increase heap sizes for master components
   - Adjust thread pool sizes
   - Optimize garbage collection settings
   - Tune network and disk I/O parameters

### Resource Management
1. **Scale Resources**
   - Add more nodes if cluster is resource-constrained
   - Increase memory/CPU on existing nodes
   - Optimize storage configuration

2. **Load Balancing**
   - Run HDFS balancer for data distribution
   - Adjust YARN capacity scheduler settings
   - Optimize HBase region distribution

### Maintenance Operations
1. **Restart Services** (during maintenance window)
   ```
   restart_service(server_url, "{cluster_name}", "SERVICE_NAME")
   ```

2. **Configuration Updates**
   - Apply performance-related configuration changes
   - Restart affected services
   - Monitor impact of changes

## Monitoring and Prevention

### Continuous Monitoring
- Set up regular health checks
- Monitor key performance metrics
- Configure appropriate alerts for performance thresholds

### Capacity Planning
- Track resource usage trends
- Plan for growth and peak usage
- Regular performance testing

### Best Practices
- Regular maintenance windows
- Gradual configuration changes
- Performance baseline establishment
- Documentation of optimizations

## Emergency Response

### Immediate Actions for Critical Performance Issues
1. Identify the most impacted services
2. Check for any critical alerts or failures
3. Consider temporary service restarts if safe
4. Isolate problematic nodes if necessary
5. Implement emergency resource allocation

### Escalation Criteria
- Multiple service failures
- Data corruption risks
- Complete cluster unavailability
- SLA breaches

Use the various Ambari MCP tools to gather detailed information and implement the recommended solutions based on your specific performance issues.
"""

    @mcp.prompt("ambari-configuration-management")
    async def configuration_management_guide(cluster_name: str) -> str:
        """Guide for managing configurations in Ambari safely.
        
        Args:
            cluster_name: Name of the cluster
        """
        return f"""# Configuration Management Best Practices for {cluster_name}

## Configuration Management Workflow

### 1. Pre-Change Assessment
**Before making any configuration changes:**

1. **Document Current State**
   ```
   get_service_config_versions(server_url, "{cluster_name}")
   ```
   - Record current configuration versions
   - Document the reason for change
   - Identify affected services and components

2. **Review Dependencies**
   - Identify services that depend on the configuration
   - Check for any ongoing operations or maintenance
   - Verify cluster health before changes

### 2. Configuration Change Process

#### Step 1: Backup Current Configuration
```
# Get current configuration for backup
get_service_config(server_url, "{cluster_name}", "CONFIG_TYPE")
```

#### Step 2: Prepare New Configuration
- Validate configuration syntax
- Test in development environment if possible
- Prepare rollback plan

#### Step 3: Apply Configuration Changes
```
# Update configuration with proper versioning
update_service_config(
    server_url, 
    "{cluster_name}", 
    "CONFIG_TYPE", 
    "{{\"property\": \"value\"}}", 
    "Description of change"
)
```

#### Step 4: Restart Affected Services
```
# Restart services to apply changes
restart_service(server_url, "{cluster_name}", "SERVICE_NAME")
```

#### Step 5: Verify Changes
```
# Run service checks to verify functionality
run_service_check(server_url, "{cluster_name}", "SERVICE_NAME")
```

### 3. Configuration Types and Common Changes

#### Core Hadoop Configurations
- **core-site.xml**: Hadoop core settings
- **hdfs-site.xml**: HDFS configuration
- **yarn-site.xml**: YARN resource management
- **mapred-site.xml**: MapReduce settings

#### Service-Specific Configurations
- **hive-site.xml**: Hive metastore and execution
- **hbase-site.xml**: HBase cluster settings
- **oozie-site.xml**: Oozie workflow engine
- **spark-defaults.conf**: Spark application settings

### 4. Common Configuration Scenarios

#### Scenario 1: Memory Tuning
**Objective:** Optimize memory allocation for better performance

**Steps:**
1. Review current memory settings
2. Calculate optimal heap sizes based on available resources
3. Update configurations gradually
4. Monitor performance impact

**Example Changes:**
- NameNode heap size
- ResourceManager heap size
- NodeManager memory allocation
- Container memory limits

#### Scenario 2: Security Configuration
**Objective:** Enable or modify security settings

**Critical Considerations:**
- Coordinate with security team
- Plan for service downtime
- Test authentication and authorization
- Update client configurations

#### Scenario 3: Performance Optimization
**Objective:** Improve cluster performance through configuration

**Focus Areas:**
- Thread pool sizes
- Connection timeouts
- Cache configurations
- Compression settings

### 5. Rollback Procedures

#### When to Rollback
- Service failures after configuration change
- Performance degradation
- Functionality issues
- Security concerns

#### Rollback Process
```
# Check available versions
get_service_config_versions(server_url, "{cluster_name}", "SERVICE_NAME")

# Rollback to previous version
rollback_service_config(
    server_url, 
    "{cluster_name}", 
    "SERVICE_NAME", 
    PREVIOUS_VERSION_NUMBER
)

# Restart services
restart_service(server_url, "{cluster_name}", "SERVICE_NAME")

# Verify rollback success
run_service_check(server_url, "{cluster_name}", "SERVICE_NAME")
```

### 6. Repository and Version Management

#### Managing Repository URLs
```
# Update repository URL for new versions
update_repository_url(
    server_url,
    "{cluster_name}",
    "HDP",
    "2.7",
    "redhat7",
    "HDP-2.7",
    "http://new-repo-url/HDP/centos7/2.x/updates/2.7.8.0"
)
```

#### Registering New Versions
```
# Register new repository version
register_repository_version(
    server_url,
    "{cluster_name}",
    "HDP",
    "2.7",
    "http://repo-url/VDF/HDP-2.7.8.0-1.xml"
)
```

### 7. Best Practices

#### Change Management
- Always use maintenance windows for major changes
- Implement changes in test environment first
- Document all changes with clear descriptions
- Coordinate with team members

#### Version Control
- Use meaningful version notes
- Track configuration history
- Maintain external backups of critical configurations
- Regular configuration audits

#### Testing and Validation
- Always run service checks after changes
- Monitor cluster health for extended period
- Validate functionality with test workloads
- Check for any new alerts or warnings

#### Emergency Procedures
- Keep rollback procedures readily available
- Maintain emergency contact information
- Document escalation procedures
- Practice configuration recovery scenarios

### 8. Monitoring Configuration Changes

#### Post-Change Monitoring
- Service health and performance
- Alert status and new warnings
- Resource utilization changes
- Application functionality

#### Long-term Tracking
- Configuration drift detection
- Performance trend analysis
- Capacity planning updates
- Security compliance verification

## Configuration Management Tools Summary

Use these Ambari MCP tools for configuration management:
- `get_service_config`: Retrieve current configurations
- `update_service_config`: Apply configuration changes
- `get_service_config_versions`: View configuration history
- `rollback_service_config`: Revert to previous versions
- `update_repository_url`: Manage repository locations
- `register_repository_version`: Add new software versions

Remember: Configuration changes can significantly impact cluster stability and performance. Always follow proper change management procedures and maintain rollback capabilities.
""" 