---
- name: Distribute hosts file to all nodes
  hosts: all
  become: yes
  tasks:
    - name: Copy hosts file
      copy:
        src: hosts
        dest: /etc/hosts
        owner: root
        group: root
        mode: '0644'

    # - name: Add hostname to /etc/hostname
    #   lineinfile:
    #     path: /etc/hostname
    #     line: "{{ inventory_hostname }}"

    # - name: Set hostname
    #   command: hostnamectl set-hostname "{{ inventory_hostname }}"
    #   when: ansible_hostname != inventory_hostname

- name: Install Docker on all nodes
  hosts: all
  become: yes
  tasks:
    - name: Install Docker using get.docker.com script
      shell: curl -fsSL https://get.docker.com | sh

    - name: Ensure Docker service is started
      service:
        name: docker
        state: started
        enabled: yes

- name: Deploy Prometheus and Grafana on master node
  hosts: master
  become: yes
  tasks:
    - name: Create Prometheus configuration directory
      file:
        path: /etc/prometheus
        state: directory

    - name: Copy Prometheus configuration file
      copy:
        src: ./prometheus/prometheus.yml
        dest: /etc/prometheus/prometheus.yml

    - name: Run Prometheus container
      docker_container:
        name: prometheus
        image: prom/prometheus
        restart: always
        ports:
          - "9090:9090"
        volumes:
          - /etc/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml

    - name: Run Grafana container
      docker_container:
        name: grafana
        image: grafana/grafana
        restart: always
        ports:
          - "3000:3000"
        env:
          GF_SECURITY_ADMIN_PASSWORD: "admin"  # Change this password
        volumes:
          - grafana-data:/var/lib/grafana

- name: Deploy Node Exporter and PowerAPI Agent on all nodes
  hosts: all
  become: yes
  tasks:
    - name: Run Node Exporter container
      docker_container:
        name: node_exporter
        image: prom/node-exporter
        restart: always
        ports:
          - "9100:9100"

    - name: Run PowerAPI Agent container
      docker_container:
        name: powerapi
        image: powerapi/powerapi
        command: |
          powerapi start formulas
            --frequency 5000
            --verbose
            --output prometheus
            --stream influxdb --uri http://localhost:9096/write?db=powerapi
        volumes:
          - /var/lib/docker/containers:/var/lib/docker/containers:ro
          - /sys:/sys:ro