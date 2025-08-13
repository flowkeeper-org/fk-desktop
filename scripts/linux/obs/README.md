# Updating OBS build

Step 1: Download the latest tar.gz

Step 2: Update `flowkeeper.spec` if needed

Step 3: Update the changelog

Step 4: Commit the changes:

```bash
osc delete <old.tar.gz>
osc add *
osc commit
```

Step 5: Check the build job status

Step 6: Test it: `sudo zypper install flowkeeper`
