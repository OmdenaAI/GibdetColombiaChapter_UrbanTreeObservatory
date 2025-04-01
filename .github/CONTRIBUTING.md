# Contributing Guidelines

First off, thanks for taking the time to contribute! ❤️  
We are thrilled that you want to help improve the project. To make your contributions smooth and collaborative, please follow these guidelines.

---

## General Contribution Workflow

### 1. **Fork the Repository**  
   - Navigate to the project repository on GitHub and click the **Fork** button at the top-right corner.
   - This creates a copy of the repository under your GitHub account.
   - Example:  
     If the repository URL is `https://github.com/OmdenaAI/GibdetColombiaChapter_UrbanTreeObservatory`, after forking it, the URL will become `https://github.com/YOUR-USERNAME/GibdetColombiaChapter_UrbanTreeObservatory`.

   **Image Example**:  
      ![Fork Button](![alt text](image-1.png))


### 2. **Clone Your Fork**  
   - Once you've forked the repo, clone it to your local machine:
     ```bash
     git clone https://github.com/YOUR-USERNAME/GibdetColombiaChapter_UrbanTreeObservatory.git
     ```
   - Navigate into the project directory:
     ```bash
     cd GibdetColombiaChapter_UrbanTreeObservatory
     ```

### 3. **Create a Feature Branch**  
   - Create a new branch for the feature/bugfix you are working on:
     ```bash
     git checkout -b feature-your-feature-name
     ```
   - Example: If you are working on a bug fix for login, you might name your branch `bugfix-login-issue`.

### 4. **Make Your Changes**  
   - Ensure your code adheres to the project's style guide and best practices.
   - Include comments to explain complex sections of the code.
   - Example: If you're adding a new function, make sure it's clean and concise:
     ```python
     def calculate_tree_area(diameter):
         """Calculate the area of a tree given its diameter."""
         area = 3.14 * (diameter / 2) ** 2
         return area
     ```

### 5. **Write Tests**  
   - **Tests**: Add tests to validate your changes.
   - If you added new functionality, make sure you create corresponding tests to verify it works.
   - Example: If you added a function like `calculate_tree_area`, write a test case:
     ```python
     def test_calculate_tree_area():
         assert calculate_tree_area(10) == 78.5
     ```

### 6. **Document Your Changes**  
   - If you are adding a new feature, update the documentation to reflect your changes.
   - Add relevant usage examples or instructions in the `README.md` or any relevant docs.
   - Example:  
     If you added a new `calculate_tree_area` function, update the documentation:
     ```markdown
     ## calculate_tree_area(diameter)
     This function calculates the area of a tree based on its diameter.
     
     **Parameters**:  
     - `diameter` (float): The diameter of the tree.

     **Returns**:  
     - The area of the tree (float).
     ```

### 7. **Submit a Pull Request (PR)**  
   - Push your changes to your fork:
     ```bash
     git push origin feature-your-feature-name
     ```
   - Open a pull request against the `main` branch of the original repository.
   - In your PR description, clearly describe what you've done, why it's necessary, and include any relevant issue number (e.g., `Fixes #123`).

   **Image Example**:  
   ![Create PR](![alt text](image-2.png))

### 8. **Get a Review**  
   - A project maintainer or task lead will review your PR.
   - Be prepared for feedback, and be open to making improvements based on the review.

---

## Code Contribution Standards

### **Protecting the `main` Branch**
- **No direct commits to `main`**. All changes must go through pull requests.
- This ensures that every change is reviewed and tested before it's merged.

### **Code Reviews**
- Every pull request must be reviewed before it is merged.
- Reviews ensure that your code adheres to best practices and that any potential issues are caught early.
- If your PR needs further changes, the reviewer will request those changes, and you’ll have the opportunity to update your PR.

### **Testing & Documentation**
- Every new feature or bug fix **must** include:
  - Tests to validate the functionality
  - Documentation explaining how to use the new feature or how the code works
- This ensures that everyone using the project will know how to use the new feature and that the code remains maintainable.

### **First-Time Contributor Guide**
-If this is your first time contributing to this project, follow the steps below to get started:
-Fork the Repository (as explained above).
-Set up the Project Locally: Follow the instructions in the README.md for setting up the project     environment.
-Read the Documentation: Before starting to code, ensure you understand the project's goals and functionality.
-Start with a Small Task: Begin with a small feature or bug fix. Check the good first issue label for easier tasks.
-Ask Questions: If you need help, ask! Open an issue or reach out to a maintainer.
-Submit Your First PR: When you're ready, submit a PR and follow the review process.
### **Code of Conduct**
This project and everyone participating in it is governed by the OmdenaAI/GibdetColombiaChapter_UrbanTreeObservatory Code of Conduct.
By participating, you are expected to uphold this code. Please report unacceptable behavior to <>.

Thank you for contributing to the project! 🎉

