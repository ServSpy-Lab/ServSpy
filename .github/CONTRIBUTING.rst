Contributing to ServSpy
==============================

Thanks!
--------
First, thank you for your interest in contributing to our project! 
We welcome contributions from the community, and we appreciate your 
efforts to help improve ServSpy.

Before contributing:
--------------------
1. Before you start to contribute, especially before opening a pull request,
   please make sure that you have already opened an issue to discuss the
   changes you want to make. This will help us understand your intentions and
   provide feedback before you start working on the code, tests or docs etc.,
   or your PR may be closed without review. In addition, please add the issue
   number or the URL in the description of your pull request, so we can easily
   track the related issue and PR.

2. Please make sure that you have already forked the ServSpy
repository.

3. After you have forked the repository, please clone it to your local machine:

.. code-block:: bash

   git clone https://github.com/<your-username>/ServSpy.git
   cd ./ServSpy

4. If there are new commits in the upstream repository that your fork
does not have, please pull the latest changes to avoid merge conflicts:

.. code-block:: bash

   git pull origin main --rebase

5. Create a new branch for your changes
   (Make sure the branch name is descriptive of the changes you are making):

.. code-block:: bash

   git checkout -b <your-branch-name>

6. When you have made your changes, commit and push them with a clear
   and descriptive commit message:

.. code-block:: bash

   git add <changed-files>
   git commit -m "Describe your changes here"
   git push origin <your-branch-name>

7. Finally, open a pull request to the original repository.
