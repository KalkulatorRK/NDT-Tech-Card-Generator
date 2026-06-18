/* NDT TechCards — main JavaScript */

"use strict";

document.addEventListener("DOMContentLoaded", function () {

  // Auto-dismiss alerts after 5 seconds
  document.querySelectorAll(".alert-dismissible").forEach(function (alert) {
    setTimeout(function () {
      var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // Confirm deletion modals
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      var msg = el.dataset.confirm || "Вы уверены?";
      if (!confirm(msg)) e.preventDefault();
    });
  });

  // Formset: add more defect rows
  var addDefectBtn = document.getElementById("add-defect-form");
  if (addDefectBtn) {
    addDefectBtn.addEventListener("click", function () {
      var formset = document.getElementById("defect-formset");
      var totalForms = document.getElementById("id_form-TOTAL_FORMS");
      var currentCount = parseInt(totalForms.value);
      var template = formset.querySelector(".defect-form-row");
      if (!template) return;

      var newRow = template.cloneNode(true);
      newRow.querySelectorAll("[name]").forEach(function (input) {
        input.name = input.name.replace(/-\d+-/, "-" + currentCount + "-");
        input.id   = input.id.replace(/-\d+-/, "-" + currentCount + "-");
        if (input.tagName !== "SELECT") input.value = "";
      });
      newRow.querySelectorAll("label[for]").forEach(function (lbl) {
        lbl.setAttribute("for", lbl.getAttribute("for").replace(/-\d+-/, "-" + currentCount + "-"));
      });

      formset.appendChild(newRow);
      totalForms.value = currentCount + 1;
    });
  }

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener("click", function (e) {
      var target = document.querySelector(a.hash);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth" });
      }
    });
  });

  // Highlight active nav link based on current URL
  var currentPath = window.location.pathname;
  document.querySelectorAll(".nav-link").forEach(function (link) {
    if (link.getAttribute("href") === currentPath) {
      link.classList.add("active");
    }
  });

});
