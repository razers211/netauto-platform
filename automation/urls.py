from django.urls import path
from . import views
from . import evpn_l2vpn_views

urlpatterns = [
    # Health check
    path('health/', views.healthcheck, name='healthcheck'),
    
    # Dashboard
    path('', views.index, name='index'),
    
    # Device management
    path('devices/', views.device_list, name='device_list'),
    path('devices/create/', views.device_create, name='device_create'),
    path('devices/<int:device_id>/', views.device_detail, name='device_detail'),
    path('devices/<int:device_id>/edit/', views.device_edit, name='device_edit'),
    path('devices/<int:device_id>/delete/', views.device_delete, name='device_delete'),
    path('devices/test/', views.device_test, name='device_test'),
    
    # Task management
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    
    # VLAN operations
    path('automation/vlan/create/', views.vlan_create, name='vlan_create'),
    path('automation/vlan/delete/', views.vlan_delete, name='vlan_delete'),
    
    # Interface operations
    path('automation/interface/', views.interface_config, name='interface_config'),
    path('automation/interface/ipv6/', views.interface_ipv6_config, name='interface_ipv6_config'),
    path('automation/interface/vlan/', views.vlan_interface_config, name='vlan_interface_config'),
    path('automation/interface/vlan/ipv6/', views.vlan_interface_ipv6_config, name='vlan_interface_ipv6_config'),
    path('automation/interface/ae/', views.ae_config, name='ae_config'),
    path('automation/huawei/eth-trunk/mlag/', views.huawei_eth_trunk_mlag, name='huawei_eth_trunk_mlag'),
    
    # Routing operations
    path('automation/routing/static/', views.routing_static, name='routing_static'),
    path('automation/routing/static6/', views.routing_static_v6, name='routing_static_v6'),
    path('automation/routing/ospf/', views.routing_ospf, name='routing_ospf'),
    
    # Show commands
    path('automation/show/<str:command_type>/', views.show_command, name='show_command'),
    
    # VRF operations
    path('automation/vrf/create/', views.vrf_create, name='vrf_create'),
    path('automation/vrf/assign-interface/', views.vrf_assign_interface, name='vrf_assign_interface'),
    
    # BGP operations
    path('automation/bgp/neighbor/', views.bgp_neighbor, name='bgp_neighbor'),
    path('automation/bgp/neighbor6/', views.bgp_neighbor_v6, name='bgp_neighbor_v6'),
    path('automation/bgp/network/', views.bgp_network, name='bgp_network'),
    path('automation/bgp/network6/', views.bgp_network_v6, name='bgp_network_v6'),
    path('automation/bgp/vrf-config/', views.bgp_vrf_config, name='bgp_vrf_config'),
    
    # Advanced BGP operations
    path('automation/bgp/route-reflector/', views.bgp_route_reflector, name='bgp_route_reflector'),
    path('automation/bgp/confederation/', views.bgp_confederation, name='bgp_confederation'),
    path('automation/bgp/multipath/', views.bgp_multipath, name='bgp_multipath'),
    path('automation/bgp/evpn/', views.bgp_evpn, name='bgp_evpn'),
    
    # Advanced OSPF operations
    path('automation/ospf/area/', views.ospf_area, name='ospf_area'),
    path('automation/ospf/authentication/', views.ospf_authentication, name='ospf_authentication'),
    path('automation/ospf/v6/', views.routing_ospf_v6, name='routing_ospf_v6'),
    
    # EVPN VXLAN operations
    path('automation/evpn/instance/', views.evpn_instance, name='evpn_instance'),
    path('automation/vxlan/tunnel/', views.vxlan_tunnel, name='vxlan_tunnel'),
    path('automation/vxlan/nve-interface/', views.nve_interface, name='nve_interface'),
    path('automation/vxlan/gateway/', views.vxlan_gateway, name='vxlan_gateway'),
    path('automation/vxlan/access-port/', views.vxlan_access_port, name='vxlan_access_port'),
    
    # Datacenter Fabric operations
    path('automation/datacenter/fabric/', views.datacenter_fabric, name='datacenter_fabric'),
    path('automation/datacenter/tenant-network/', views.tenant_network, name='tenant_network'),
    path('automation/datacenter/external-connectivity/', views.external_connectivity, name='external_connectivity'),
    path('automation/datacenter/multi-tenant/', views.multi_tenant_deployment, name='multi_tenant_deployment'),
    path('automation/datacenter/fabric/deploy-all/', views.full_fabric_deploy, name='full_fabric_deploy'),
    
    # EVPN/L2VPN operations
    path('automation/l2vpn/l2vpws/', evpn_l2vpn_views.l2vpws, name='l2vpws'),
    path('automation/l2vpn/vpls/', evpn_l2vpn_views.l2vpn_vpls, name='l2vpn_vpls'),
    path('automation/evpn/instance/config/', evpn_l2vpn_views.evpn_instance, name='evpn_instance_config'),
    path('automation/evpn/bridge-domain/', evpn_l2vpn_views.bridge_domain, name='bridge_domain_config'),
    
    # API endpoints
    path('api/tasks/<int:task_id>/status/', views.api_task_status, name='api_task_status'),
    path('api/devices/<int:device_id>/interfaces/', views.api_device_interfaces, name='api_device_interfaces'),
    path('api/devices/<int:device_id>/vrfs/', views.api_device_vrfs, name='api_device_vrfs'),
]
