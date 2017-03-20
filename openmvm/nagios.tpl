define host {
      notifications_enabled           1       ; Host notifications are enabled
      event_handler_enabled           1       ; Host event handler is enabled
      flap_detection_enabled          1       ; Flap detection is enabled
      failure_prediction_enabled      1       ; Failure prediction is enabled
      process_perf_data               1       ; Process performance data
      retain_status_information       1       ; Retain status information across program restarts
      retain_nonstatus_information    1       ; Retain non-status information across program restarts
      max_check_attempts              10
      notification_interval           0
      notification_period             24x7
      notification_options            d,u,r
      contact_groups                  admins
      host_name                      {{host}}
      alias                          {{ID}}
}

define service {
        active_checks_enabled          0
        check_command                  return-virt-cpu
        check_freshness                1
        check_interval                 1
        contact_groups                 openstack
        freshness_threshold            65
        host_name                      {{host}}
        max_check_attempts             2
        notifications_enabled          0
        passive_checks_enabled         1
        process_perf_data              0
        retry_interval                 1
        service_description            cpu
        use                            generic-service
}

define service {
        active_checks_enabled          0
        check_command                  return-virt-mem
        check_freshness                1
        check_interval                 1
        contact_groups                 openstack
        freshness_threshold            65
        host_name                      {{host}}
        max_check_attempts             2
        notifications_enabled          0
        passive_checks_enabled         1
        process_perf_data              0
        retry_interval                 1
        service_description            mem
        use                            generic-service
}


define service {
        active_checks_enabled          0
        check_command                  return-virt-disk
        check_freshness                1
        check_interval                 1
        contact_groups                 openstack
        freshness_threshold            65
        host_name                      {{host}}
        max_check_attempts             2
        notifications_enabled          0
        passive_checks_enabled         1
        process_perf_data              0
        retry_interval                 1
        service_description            diskio
        use                            generic-service
}


define service {
        active_checks_enabled          0
        check_command                  return-virt-net
        check_freshness                1
        check_interval                 1
        contact_groups                 openstack
        freshness_threshold            65
        host_name                      {{host}}
        max_check_attempts             2
        notifications_enabled          0
        passive_checks_enabled         1
        process_perf_data              0
        retry_interval                 1
        service_description            netio
        use                            generic-service
}
