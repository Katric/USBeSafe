# USBeSafe Guest Daemon (usbesafed-vm)

## Setup OpenRC daemon (in guest)

Copy the daemon script to `/usr/local/bin/` and make it executable. Replace the content with `usbesafed-vm.py`:

```sh
cat > /usr/local/bin/usbesafed-vm << 'EOF'
(paste content of usbesafed-vm.py here)
EOF
chmod +x /usr/local/bin/usbesafed-vm
```

Copy the OpenRC init script. Replace the content with `usbesafed-vm.init`:

```sh
cat > /etc/init.d/usbesafed-vm << 'EOF'
(paste content of usbesafed-vm.init here)
EOF
chmod +x /etc/init.d/usbesafed-vm
rc-update add usbesafed-vm default
rc-service usbesafed-vm start
```

## Check status

```sh
rc-status
rc-service usbesafed-vm status
```




